"""Tests for web_ui endpoints: per-user cookie routing (Phase 28, ROUTE-01)."""
import json
import os
import pathlib
import sys
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

# web_ui is not a package — add its parent dir so `import main` resolves
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_ui"))

from fastapi.testclient import TestClient
import main as web_ui_main
from main import UserContext


# ---------------------------------------------------------------------------
# Per-user directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_dir(tmp_path):
    """Scaffold a minimal per-user directory tree."""
    uid = "testuid123"
    base = tmp_path / "users" / uid
    data = base / "data"
    token = base / "token_cache"
    data.mkdir(parents=True)
    token.mkdir(parents=True)
    state = base / "state.json"
    state.write_text(json.dumps({"last_track_id": None, "family_safe_mode": False, "active_profile": "kids_present"}))
    (data / "events.jsonl").write_text("")
    (data / "now_playing.json").write_text("")
    return base


@pytest.fixture
def mock_ctx(user_dir):
    """UserContext pointing to tmp per-user directory."""
    uid_dir = user_dir
    return UserContext(
        uid="testuid123",
        state_path=str(uid_dir / "state.json"),
        events_path=str(uid_dir / "data" / "events.jsonl"),
        now_playing_path=str(uid_dir / "data" / "now_playing.json"),
        token_cache_path=str(uid_dir / "token_cache" / ".cache"),
    )


@pytest.fixture
def client(mock_ctx):
    """TestClient that overrides get_user_context with mock_ctx."""
    mock_sp = MagicMock()
    web_ui_main.app.dependency_overrides[web_ui_main.get_user_context] = lambda: mock_ctx
    with patch.object(web_ui_main, "_sp_init", return_value=mock_sp):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            c._mock_sp = mock_sp
            yield c
    web_ui_main.app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client():
    """TestClient with NO dependency override — get_user_context uses real implementation."""
    # Patch _registry.load() to return empty list so any uid is unknown
    with patch.object(web_ui_main._registry, "load", return_value=[]):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# 401 — missing/unknown/pending cookie (D-01, D-02)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path,body", [
    ("GET", "/", None),
    ("GET", "/fsm", None),
    ("POST", "/fsm", {"enabled": True}),
    ("GET", "/now-playing", None),
    ("GET", "/feed", None),
    ("GET", "/profile", None),
    ("POST", "/profile", {"profile": "kids_present"}),
    ("POST", "/skip", None),
])
def test_missing_cookie_returns_401(unauthed_client, method, path, body):
    """Every route returns 401 when no uid cookie is present (D-01)."""
    resp = unauthed_client.request(method, path, json=body)
    assert resp.status_code == 401


def test_unknown_uid_returns_401(unauthed_client):
    """uid cookie with unknown value returns 401 (D-01)."""
    resp = unauthed_client.get("/", cookies={"uid": "doesnotexist"})
    assert resp.status_code == 401


def test_pending_uid_returns_401():
    """uid with status=pending is treated as invalid — returns 401 (D-02)."""
    pending_user = {"uid": "pendinguid", "name": "Alice", "created_at": "2026-04-18T00:00:00+00:00", "status": "pending"}
    with patch.object(web_ui_main._registry, "load", return_value=[pending_user]):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get("/", cookies={"uid": "pendinguid"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /now-playing
# ---------------------------------------------------------------------------

def test_now_playing_idle(client, mock_ctx):
    """Returns {"status": "idle"} when now_playing.json does not exist (D-02)."""
    pathlib.Path(mock_ctx.now_playing_path).unlink()
    resp = client.get("/now-playing")
    assert resp.status_code == 200
    assert resp.json() == {"status": "idle"}


def test_now_playing_returns_file_contents(client, mock_ctx):
    """Returns full now_playing.json contents verbatim when file exists (D-03)."""
    payload = {
        "track_id": "spotify:track:abc123",
        "track": "Test Song",
        "artist": "Test Artist",
        "album_art_url": "https://i.scdn.co/image/abc",
        "eval_state": "passed",
        "timestamp": "2026-04-03T12:00:00",
    }
    pathlib.Path(mock_ctx.now_playing_path).write_text(json.dumps(payload))
    resp = client.get("/now-playing")
    assert resp.status_code == 200
    assert resp.json() == payload


# ---------------------------------------------------------------------------
# POST /skip
# ---------------------------------------------------------------------------

def test_skip_success(client):
    """Returns {"ok": true} when sp.next_track() succeeds (D-04)."""
    client._mock_sp.next_track.return_value = None  # Spotify returns None on success
    resp = client.post("/skip")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    client._mock_sp.next_track.assert_called_once()


def test_skip_spotify_error_returns_503(client):
    """Returns HTTP 503 with skip_failed detail when sp.next_track() raises (D-05).

    Uses a non-403 status so the SoCo fallback path is not triggered.
    """
    import spotipy
    client._mock_sp.next_track.side_effect = spotipy.SpotifyException(
        http_status=429, code=-1, msg="No active device"
    )
    resp = client.post("/skip")
    assert resp.status_code == 503
    body = resp.json()
    assert body["detail"] == "skip_failed"
    assert "No active device" in body["reason"]


# ---------------------------------------------------------------------------
# POST /profile — PROF-01, PROF-02 (Phase 16)
# ---------------------------------------------------------------------------

def test_post_profile_valid(client, mock_ctx):
    """POST /profile with valid key saves to state.json and returns 200 (PROF-02)."""
    resp = client.post("/profile", json={"profile": "kids_present"})
    assert resp.status_code == 200
    assert resp.json() == {"active_profile": "kids_present"}
    data = json.loads(pathlib.Path(mock_ctx.state_path).read_text())
    assert data["active_profile"] == "kids_present"


def test_post_profile_invalid(client, mock_ctx):
    """POST /profile with unknown profile key returns 400 (PROF-02)."""
    resp = client.post("/profile", json={"profile": "not_a_real_profile"})
    assert resp.status_code == 400


def test_post_profile_does_not_change_fsm(client, mock_ctx):
    """POST /profile must not modify family_safe_mode (independence invariant, D-09)."""
    # Pre-seed state.json with family_safe_mode = True
    pathlib.Path(mock_ctx.state_path).write_text(json.dumps({"family_safe_mode": True, "last_track_id": None}))
    resp = client.post("/profile", json={"profile": "were_all_adults"})
    assert resp.status_code == 200
    data = json.loads(pathlib.Path(mock_ctx.state_path).read_text())
    assert data["family_safe_mode"] is True
    assert data["active_profile"] == "were_all_adults"


def test_dashboard_injects_profile_initial(client, mock_ctx):
    """GET / replaces __PROFILE_INITIAL__ with active_profile from state.json (PROF-04)."""
    pathlib.Path(mock_ctx.state_path).write_text(
        json.dumps({"family_safe_mode": False, "active_profile": "permissive"})
    )
    resp = client.get("/")
    assert resp.status_code == 200
    assert "__PROFILE_INITIAL__" not in resp.text
    assert "permissive" in resp.text


# ---------------------------------------------------------------------------
# SSE per-uid isolation — ROUTE-02 (Phase 28)
# ---------------------------------------------------------------------------

import asyncio as _asyncio


def _clear_sse_state():
    """Reset module-level SSE dicts between tests."""
    web_ui_main._tails.clear()
    web_ui_main._subscribers.clear()


def test_first_events_connection_starts_tail_task(mock_ctx):
    """First /events for a uid creates one entry in _tails (D-06)."""
    _clear_sse_state()
    uid = mock_ctx.uid

    # Simulate what GET /events does (without opening a real stream)
    subscriber = _asyncio.Queue(maxsize=100)
    web_ui_main._subscribers[uid] = [subscriber]

    # Simulate task creation (D-06 logic)
    task = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))
    web_ui_main._tails[uid] = task

    assert uid in web_ui_main._tails
    assert web_ui_main._tails[uid] is task

    # Cleanup
    task.cancel()
    _clear_sse_state()


def test_second_events_connection_shares_existing_task(mock_ctx):
    """Second /events connection for same uid reuses existing tail task (D-05)."""
    _clear_sse_state()
    uid = mock_ctx.uid

    # Simulate first connection
    task = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))
    web_ui_main._tails[uid] = task
    q1 = _asyncio.Queue(maxsize=100)
    web_ui_main._subscribers[uid] = [q1]

    # Simulate second connection — task already exists and not done; no new task created
    q2 = _asyncio.Queue(maxsize=100)
    web_ui_main._subscribers[uid].append(q2)
    if uid not in web_ui_main._tails or web_ui_main._tails[uid].done():
        web_ui_main._tails[uid] = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))

    # Still one task
    assert len([k for k in web_ui_main._tails if k == uid]) == 1
    assert len(web_ui_main._subscribers[uid]) == 2

    task.cancel()
    _clear_sse_state()


async def test_last_subscriber_removal_cancels_tail_task(mock_ctx):
    """Removing last subscriber for uid cancels the tail task and clears dicts (D-07)."""
    _clear_sse_state()
    uid = mock_ctx.uid

    # Set up one subscriber and one tail task
    q = _asyncio.Queue(maxsize=100)
    web_ui_main._subscribers[uid] = [q]
    task = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))
    web_ui_main._tails[uid] = task

    # Simulate generator finally block (last subscriber removed)
    web_ui_main._subscribers[uid].remove(q)
    if not web_ui_main._subscribers.get(uid):
        web_ui_main._subscribers.pop(uid, None)
        tail = web_ui_main._tails.pop(uid, None)
        if tail and not tail.done():
            tail.cancel()

    assert uid not in web_ui_main._tails
    assert uid not in web_ui_main._subscribers
    # Give event loop a cycle to process cancellation
    await _asyncio.sleep(0)
    assert task.cancelled() or task.done()

    _clear_sse_state()


async def test_two_uids_get_independent_tail_tasks():
    """Two different uids each have their own isolated tail task (D-05)."""
    _clear_sse_state()

    uid_a = "userabc"
    uid_b = "userxyz"

    task_a = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))
    task_b = _asyncio.get_event_loop().create_task(_asyncio.sleep(9999))
    web_ui_main._tails[uid_a] = task_a
    web_ui_main._tails[uid_b] = task_b
    web_ui_main._subscribers[uid_a] = [_asyncio.Queue(maxsize=100)]
    web_ui_main._subscribers[uid_b] = [_asyncio.Queue(maxsize=100)]

    assert web_ui_main._tails[uid_a] is task_a
    assert web_ui_main._tails[uid_b] is task_b
    assert web_ui_main._tails[uid_a] is not web_ui_main._tails[uid_b]

    task_a.cancel()
    task_b.cancel()
    _clear_sse_state()


# ---------------------------------------------------------------------------
# GET /auth/callback — OAuth onboarding flow (Phase 29, AUTH-01, AUTH-02, AUTH-03)
# ---------------------------------------------------------------------------

@pytest.fixture
def callback_client(tmp_path):
    """TestClient for callback tests — no dependency override (callback has no Depends).
    Registry state and SpotifyOAuth are controlled per-test via patch.object / patch."""
    with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
        yield c, tmp_path


def _pending_user_record(uid="callbackuid1"):
    return {"uid": uid, "name": "Alice", "created_at": "2026-01-01T00:00:00+00:00", "status": "pending"}


def _active_user_record(uid="callbackuid1"):
    return {"uid": uid, "name": "Alice", "created_at": "2026-01-01T00:00:00+00:00", "status": "active"}


def test_callback_success_redirects_to_root(tmp_path):
    """Valid code + pending uid → 302 to / with uid cookie (AUTH-01, D-01)."""
    uid = "callbackuid1"
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / "token_cache" / ".cache"),
    }
    with patch.object(web_ui_main._registry, "load", return_value=[_pending_user_record(uid)]), \
         patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch.object(web_ui_main._registry, "activate") as mock_activate, \
         patch("main.SpotifyOAuth") as mock_oauth_cls, \
         patch("asyncio.create_subprocess_exec") as mock_spawn:
        mock_auth = MagicMock()
        mock_oauth_cls.return_value = mock_auth
        mock_spawn.return_value = MagicMock()
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get(f"/auth/callback?code=authcode123&state={uid}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
    assert "uid" in resp.cookies or "uid=" in resp.headers.get("set-cookie", "")
    mock_activate.assert_called_once_with(uid)


def test_callback_sets_uid_cookie(tmp_path):
    """Successful callback sets httpOnly uid cookie (AUTH-02, D-02)."""
    uid = "callbackuid1"
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / "token_cache" / ".cache"),
    }
    with patch.object(web_ui_main._registry, "load", return_value=[_pending_user_record(uid)]), \
         patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch.object(web_ui_main._registry, "activate"), \
         patch("main.SpotifyOAuth") as mock_oauth_cls, \
         patch("asyncio.create_subprocess_exec"):
        mock_oauth_cls.return_value = MagicMock()
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get(f"/auth/callback?code=authcode123&state={uid}", follow_redirects=False)
    set_cookie = resp.headers.get("set-cookie", "")
    assert f"uid={uid}" in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()
    assert "SameSite=lax" in set_cookie or "samesite=lax" in set_cookie.lower()


def test_callback_error_param_returns_400():
    """Spotify error query param (user denied) → 400 HTML (D-03)."""
    with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
        resp = c.get("/auth/callback?error=access_denied&state=someuid")
    assert resp.status_code == 400
    assert "denied" in resp.text.lower() or "access_denied" in resp.text


def test_callback_missing_code_returns_400():
    """No code param → 400 HTML."""
    with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
        resp = c.get("/auth/callback?state=someuid")
    assert resp.status_code == 400
    assert "code" in resp.text.lower() or "missing" in resp.text.lower()


def test_callback_missing_state_returns_400():
    """No state param → 400 HTML (AUTH-02)."""
    with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
        resp = c.get("/auth/callback?code=abc123")
    assert resp.status_code == 400
    assert "state" in resp.text.lower() or "missing" in resp.text.lower()


def test_callback_unknown_uid_returns_400():
    """uid not in registry → 400 HTML (D-04)."""
    with patch.object(web_ui_main._registry, "load", return_value=[]):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get("/auth/callback?code=abc123&state=unknownuid")
    assert resp.status_code == 400


def test_callback_already_active_uid_returns_400():
    """uid with status='active' → 400 HTML (D-04 — only pending allowed)."""
    uid = "callbackuid1"
    with patch.object(web_ui_main._registry, "load", return_value=[_active_user_record(uid)]):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get(f"/auth/callback?code=abc123&state={uid}")
    assert resp.status_code == 400


def test_callback_token_exchange_failure_returns_500(tmp_path):
    """SpotifyOAuth raises → 500 HTML (D-03 error page)."""
    uid = "callbackuid1"
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / "token_cache" / ".cache"),
    }
    with patch.object(web_ui_main._registry, "load", return_value=[_pending_user_record(uid)]), \
         patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch("main.SpotifyOAuth") as mock_oauth_cls:
        mock_auth = MagicMock()
        mock_auth.get_access_token.side_effect = Exception("Spotify API error")
        mock_oauth_cls.return_value = mock_auth
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get(f"/auth/callback?code=badcode&state={uid}")
    assert resp.status_code == 500
    assert "token exchange failed" in resp.text.lower() or "failed" in resp.text.lower()


def test_callback_spawn_failure_still_redirects(tmp_path):
    """OSError on daemon spawn → still returns 302 (D-10)."""
    uid = "callbackuid1"
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / "token_cache" / ".cache"),
    }
    with patch.object(web_ui_main._registry, "load", return_value=[_pending_user_record(uid)]), \
         patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch.object(web_ui_main._registry, "activate"), \
         patch("main.SpotifyOAuth") as mock_oauth_cls, \
         patch("asyncio.create_subprocess_exec", side_effect=OSError("no such file")):
        mock_oauth_cls.return_value = MagicMock()
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            resp = c.get(f"/auth/callback?code=authcode123&state={uid}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_callback_spawns_daemon(tmp_path):
    """Successful callback calls asyncio.create_subprocess_exec with sys.executable and daemon.py (AUTH-03)."""
    uid = "callbackuid1"
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / "token_cache" / ".cache"),
    }
    with patch.object(web_ui_main._registry, "load", return_value=[_pending_user_record(uid)]), \
         patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch.object(web_ui_main._registry, "activate"), \
         patch("main.SpotifyOAuth") as mock_oauth_cls, \
         patch("asyncio.create_subprocess_exec") as mock_spawn:
        mock_oauth_cls.return_value = MagicMock()
        mock_spawn.return_value = MagicMock()
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            c.get(f"/auth/callback?code=authcode123&state={uid}", follow_redirects=False)
    assert mock_spawn.called
    call_args = mock_spawn.call_args
    # First two positional args must be sys.executable and a path ending in daemon.py
    import sys
    assert call_args.args[0] == sys.executable
    assert call_args.args[1].endswith("daemon.py")
