"""Spotify Family Safe Mode — Web UI Service (Phase 3).

FastAPI app serving the dashboard HTML and providing:
  GET  /          -> HTML dashboard (template rendered by Plan 03-02)
  GET  /events    -> SSE stream of skip events from daemon's shared queue
  GET  /fsm       -> current FSM state {"family_safe_mode": bool}
  POST /fsm       -> toggle FSM {"enabled": bool} -> {"family_safe_mode": bool}

Shares skip_event_queue with daemon.py when run in-process.
When run as a separate process (docker-compose web_ui service),
the queue bridge is a file-based fallback (Phase 3 extension point).

D-05: Runs as second service in docker-compose.yml, network_mode: host.
D-08: Consumes skip_event_queue from daemon module (in-process import).
D-09: FSM toggle uses same read-merge-write pattern as daemon save_state().
D-10: No auth — LAN only.
"""
import asyncio
import json
import logging
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

STATE_PATH = os.environ.get("STATE_PATH", "state.json")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

app = FastAPI(title="Spotify Family Safe Mode", docs_url=None, redoc_url=None)

# ---------------------------------------------------------------------------
# File-based IPC bridge — daemon writes skip_events.jsonl; we tail it here.
# Replaces the broken in-process asyncio.Queue import (Gap-2 fix).
# Both containers share the file via a docker-compose ./data volume mount.
# ---------------------------------------------------------------------------
SKIP_EVENTS_PATH = os.environ.get("SKIP_EVENTS_PATH", "data/skip_events.jsonl")

# Each SSE client gets its own subscriber queue (maxsize=100).
_subscribers: list[asyncio.Queue] = []


async def _file_tail() -> None:
    """Tail skip_events.jsonl and push new JSON-line events to all SSE subscribers.

    Starts reading from the END of the file on startup (skips history) so the browser
    only sees events that occur while it is connected — consistent with the original
    in-process queue behaviour.
    """
    log.info("web_ui: tailing %s for SSE events", SKIP_EVENTS_PATH)
    # Wait until the file exists (daemon may start slightly after web_ui)
    while not os.path.exists(SKIP_EVENTS_PATH):
        await asyncio.sleep(1)

    with open(SKIP_EVENTS_PATH) as fh:
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
                _subscribers.remove(q)


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_file_tail())


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
    """Read-merge-write: never drops keys the daemon owns. Direct write (no atomic rename
    — os.replace() raises EBUSY on bind-mounted files on Linux, per Phase 1 decision)."""
    on_disk = _load_state()
    on_disk.update(fields)
    with open(STATE_PATH, "w") as f:
        json.dump(on_disk, f)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Serve the dashboard HTML. Template file created in Plan 03-02."""
    template_path = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(template_path) as f:
            html = f.read()
    except FileNotFoundError:
        html = "<html><body><p>Dashboard template not yet installed (Plan 03-02).</p></body></html>"
    # Inject current FSM state so the button renders correctly on first load
    state = _load_state()
    fsm_on = str(state.get("family_safe_mode", False)).lower()
    html = html.replace("__FSM_INITIAL__", fsm_on)
    return HTMLResponse(content=html)


async def _sse_event_generator(subscriber: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings from the subscriber queue indefinitely."""
    try:
        while True:
            event = await subscriber.get()
            payload = json.dumps(event)
            yield f"data: {payload}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        try:
            _subscribers.remove(subscriber)
        except ValueError:
            pass


@app.get("/events")
async def sse_events() -> StreamingResponse:
    """SSE endpoint. Browser opens EventSource('/events'); daemon pushes skip events.
    Each client gets its own asyncio.Queue (max 100 items) to prevent slow clients
    from blocking the broadcaster."""
    subscriber: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(subscriber)
    return StreamingResponse(
        _sse_event_generator(subscriber),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class FSMRequest(BaseModel):
    enabled: bool


@app.get("/fsm")
async def get_fsm() -> JSONResponse:
    """Return current FSM state."""
    state = _load_state()
    return JSONResponse({"family_safe_mode": state.get("family_safe_mode", False)})


@app.post("/fsm")
async def set_fsm(body: FSMRequest) -> JSONResponse:
    """Toggle FSM. Reads state.json, merges {family_safe_mode: bool}, writes back (D-09).
    Returns updated state."""
    try:
        _save_state_merge({"family_safe_mode": body.enabled})
    except OSError as exc:
        log.error("POST /fsm write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"family_safe_mode": body.enabled})
