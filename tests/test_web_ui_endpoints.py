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
