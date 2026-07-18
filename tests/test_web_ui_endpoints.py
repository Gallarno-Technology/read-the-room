"""Tests for web_ui endpoints — single-user model.

All on-disk paths are process-global module vars (STATE_PATH, EVENTS_PATH,
NOW_PLAYING_PATH, SPOTIFY_CACHE_PATH). Tests point them at tmp files via
monkeypatch. There is no per-user cookie/registry layer anymore.
"""

import asyncio as _asyncio
import json
import os
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# web_ui is not a package — add its parent dir so `import main` resolves
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_ui"),
)

import main as web_ui_main
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures — global paths pointed at a tmp tree
# ---------------------------------------------------------------------------


@pytest.fixture
def paths(tmp_path, monkeypatch):
    """Point every web_ui global path at a tmp tree and return the paths."""
    data = tmp_path / "data"
    token = tmp_path / "token_cache"
    data.mkdir()
    token.mkdir()
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "last_track_id": None,
                "family_safe_mode": False,
                "active_profile": "kids_present",
            }
        )
    )
    events = data / "events.jsonl"
    events.write_text("")
    now_playing = data / "now_playing.json"
    cache = token / ".cache"

    monkeypatch.setattr(web_ui_main, "STATE_PATH", str(state))
    monkeypatch.setattr(web_ui_main, "EVENTS_PATH", str(events))
    monkeypatch.setattr(web_ui_main, "NOW_PLAYING_PATH", str(now_playing))
    monkeypatch.setattr(web_ui_main, "SPOTIFY_CACHE_PATH", str(cache))
    return {
        "state": state,
        "events": events,
        "now_playing": now_playing,
        "cache": cache,
    }


@pytest.fixture
def authed(paths):
    """Write a token cache so _is_authenticated() is True."""
    paths["cache"].write_text('{"access_token": "x"}')
    return paths


@pytest.fixture
def client(paths):
    """TestClient with _sp_init mocked out."""
    mock_sp = MagicMock()
    with patch.object(web_ui_main, "_sp_init", return_value=mock_sp):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            c._mock_sp = mock_sp
            yield c


# ---------------------------------------------------------------------------
# GET / — dashboard vs onboarding redirect
# ---------------------------------------------------------------------------


def test_dashboard_redirects_when_unauthenticated(client, paths):
    """GET / with no token cache redirects to /auth/login."""
    assert not paths["cache"].exists()
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


def test_dashboard_serves_html_when_authenticated(client, authed):
    """GET / with a token cache returns 200 dashboard HTML."""
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_injects_profile_initial(client, authed):
    """GET / replaces __PROFILE_INITIAL__ with active_profile from state.json (PROF-04)."""
    authed["state"].write_text(
        json.dumps({"family_safe_mode": False, "active_profile": "permissive"})
    )
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "__PROFILE_INITIAL__" not in resp.text
    assert "permissive" in resp.text


# ---------------------------------------------------------------------------
# GET /now-playing
# ---------------------------------------------------------------------------


def test_now_playing_idle(client, paths):
    """Returns {"status": "idle"} when now_playing.json does not exist (D-02)."""
    assert not paths["now_playing"].exists()
    resp = client.get("/now-playing")
    assert resp.status_code == 200
    assert resp.json() == {"status": "idle"}


def test_now_playing_returns_file_contents(client, paths):
    """Returns full now_playing.json contents verbatim when file exists (D-03)."""
    payload = {
        "track_id": "spotify:track:abc123",
        "track": "Test Song",
        "artist": "Test Artist",
        "album_art_url": "https://i.scdn.co/image/abc",
        "eval_state": "passed",
        "timestamp": "2026-04-03T12:00:00",
    }
    paths["now_playing"].write_text(json.dumps(payload))
    resp = client.get("/now-playing")
    assert resp.status_code == 200
    assert resp.json() == payload


# ---------------------------------------------------------------------------
# GET /fsm & POST /fsm
# ---------------------------------------------------------------------------


def test_get_fsm(client, paths):
    resp = client.get("/fsm")
    assert resp.status_code == 200
    assert resp.json() == {"family_safe_mode": False}


def test_post_fsm_toggles_state(client, paths):
    resp = client.post("/fsm", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json() == {"family_safe_mode": True}
    data = json.loads(paths["state"].read_text())
    assert data["family_safe_mode"] is True
    # daemon-owned keys preserved
    assert "active_profile" in data


# ---------------------------------------------------------------------------
# POST /skip
# ---------------------------------------------------------------------------


def test_skip_success(client):
    """Returns {"ok": true} when sp.next_track() succeeds (D-04)."""
    client._mock_sp.next_track.return_value = None
    resp = client.post("/skip")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    client._mock_sp.next_track.assert_called_once()


def test_skip_spotify_error_returns_503(client):
    """Returns HTTP 503 with skip_failed detail when sp.next_track() raises (D-05)."""
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


def test_post_profile_valid(client, paths):
    resp = client.post("/profile", json={"profile": "kids_present"})
    assert resp.status_code == 200
    assert resp.json() == {"active_profile": "kids_present"}
    data = json.loads(paths["state"].read_text())
    assert data["active_profile"] == "kids_present"


def test_post_profile_invalid(client, paths):
    resp = client.post("/profile", json={"profile": "not_a_real_profile"})
    assert resp.status_code == 400


def test_post_profile_does_not_change_fsm(client, paths):
    """POST /profile must not modify family_safe_mode (independence invariant, D-09)."""
    paths["state"].write_text(
        json.dumps({"family_safe_mode": True, "last_track_id": None})
    )
    resp = client.post("/profile", json={"profile": "were_all_adults"})
    assert resp.status_code == 200
    data = json.loads(paths["state"].read_text())
    assert data["family_safe_mode"] is True
    assert data["active_profile"] == "were_all_adults"


# ---------------------------------------------------------------------------
# SSE — single-tail infrastructure + poll_kick
# ---------------------------------------------------------------------------


def _clear_sse_state():
    web_ui_main._subscribers.clear()
    web_ui_main._tail_task = None


def test_sse_connect_touches_poll_kick(paths):
    """A new /events connection touches poll_kick next to state.json.

    The daemon consumes that file at the end of its next poll iteration so the
    dashboard hydrates promptly instead of waiting up to POLL_INTERVAL_IDLE.

    We invoke the handler coroutine directly (rather than via TestClient.stream)
    because the SSE generator blocks on subscriber.get(); we only care that the
    file exists by the time StreamingResponse is constructed.
    """
    _clear_sse_state()
    # Kick lives in the events/data dir — the volume shared with the daemon container.
    expected_kick = pathlib.Path(os.path.dirname(str(paths["events"]))) / "poll_kick"
    if expected_kick.exists():
        expected_kick.unlink()

    response = _asyncio.run(web_ui_main.sse_events())
    try:
        assert response.status_code == 200
        assert expected_kick.exists(), f"poll_kick not created at {expected_kick}"
    finally:
        if web_ui_main._tail_task and not web_ui_main._tail_task.done():
            web_ui_main._tail_task.cancel()
        if expected_kick.exists():
            expected_kick.unlink()
        _clear_sse_state()


def test_sse_connect_registers_subscriber_and_tail(paths):
    """A new /events connection appends a subscriber and starts the tail task."""
    _clear_sse_state()
    _asyncio.run(web_ui_main.sse_events())
    try:
        assert len(web_ui_main._subscribers) == 1
        assert web_ui_main._tail_task is not None
    finally:
        if web_ui_main._tail_task and not web_ui_main._tail_task.done():
            web_ui_main._tail_task.cancel()
        _clear_sse_state()


# ---------------------------------------------------------------------------
# GET /auth/login
# ---------------------------------------------------------------------------


def test_auth_login_redirects_to_spotify(client, paths):
    """GET /auth/login returns 302 to Spotify's authorize URL."""
    with patch("main.SpotifyOAuth") as mock_oauth_cls:
        mock_auth = MagicMock()
        mock_auth.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?x=1"
        )
        mock_oauth_cls.return_value = mock_auth
        resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://accounts.spotify.com/authorize")


# ---------------------------------------------------------------------------
# GET /auth/callback — single-user Authorization Code flow
# ---------------------------------------------------------------------------


def test_callback_success_redirects_to_root(client, paths):
    """Valid code + matching state → 302 to / and token exchange runs."""
    with patch("main.SpotifyOAuth") as mock_oauth_cls:
        mock_auth = MagicMock()
        mock_oauth_cls.return_value = mock_auth
        resp = client.get(
            f"/auth/callback?code=authcode123&state={web_ui_main._OAUTH_STATE}",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
    mock_auth.get_access_token.assert_called_once()


def test_callback_error_param_returns_400(client):
    """Spotify error query param (user denied) → 400 HTML."""
    resp = client.get(
        f"/auth/callback?error=access_denied&state={web_ui_main._OAUTH_STATE}"
    )
    assert resp.status_code == 400
    assert "denied" in resp.text.lower() or "access_denied" in resp.text


def test_callback_missing_code_returns_400(client):
    resp = client.get(f"/auth/callback?state={web_ui_main._OAUTH_STATE}")
    assert resp.status_code == 400
    assert "code" in resp.text.lower() or "missing" in resp.text.lower()


def test_callback_state_mismatch_returns_400(client):
    """A state that does not match the fixed token → 400 HTML."""
    resp = client.get("/auth/callback?code=abc123&state=wrongstate")
    assert resp.status_code == 400
    assert "state" in resp.text.lower()


def test_callback_token_exchange_failure_returns_500(client):
    """SpotifyOAuth raises → 500 HTML error page."""
    with patch("main.SpotifyOAuth") as mock_oauth_cls:
        mock_auth = MagicMock()
        mock_auth.get_access_token.side_effect = Exception("Spotify API error")
        mock_oauth_cls.return_value = mock_auth
        resp = client.get(
            f"/auth/callback?code=badcode&state={web_ui_main._OAUTH_STATE}"
        )
    assert resp.status_code == 500
    assert "failed" in resp.text.lower()
