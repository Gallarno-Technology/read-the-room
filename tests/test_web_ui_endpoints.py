"""Tests for Phase 7 web_ui endpoints: GET /now-playing, POST /skip (SKIP-02, SKIP-03)."""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# web_ui is not a package — add its parent dir so `import main` resolves
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_ui"))

from fastapi.testclient import TestClient
import main as web_ui_main


@pytest.fixture
def now_playing_path(tmp_path, monkeypatch):
    """Redirect NOW_PLAYING_PATH to a tmp file location."""
    np_file = tmp_path / "now_playing.json"
    monkeypatch.setattr(web_ui_main, "NOW_PLAYING_PATH", str(np_file))
    return np_file


@pytest.fixture
def client(now_playing_path):
    """TestClient with a fresh spotipy mock."""
    mock_sp = MagicMock()
    # Patch _sp_init so skip_track() uses mock instead of real Spotify client
    monkeypatch_sp = patch.object(web_ui_main, "_sp_init", return_value=mock_sp)
    with monkeypatch_sp:
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            c._mock_sp = mock_sp
            yield c


# ---------------------------------------------------------------------------
# GET /now-playing
# ---------------------------------------------------------------------------

def test_now_playing_idle(client, now_playing_path):
    """Returns {"status": "idle"} when now_playing.json does not exist (D-02)."""
    # now_playing_path does not exist yet (tmp file not created)
    resp = client.get("/now-playing")
    assert resp.status_code == 200
    assert resp.json() == {"status": "idle"}


def test_now_playing_returns_file_contents(client, now_playing_path):
    """Returns full now_playing.json contents verbatim when file exists (D-03)."""
    payload = {
        "track_id": "spotify:track:abc123",
        "track": "Test Song",
        "artist": "Test Artist",
        "album_art_url": "https://i.scdn.co/image/abc",
        "eval_state": "passed",
        "timestamp": "2026-04-03T12:00:00",
    }
    now_playing_path.write_text(json.dumps(payload))
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
# State path fixture for profile tests
# ---------------------------------------------------------------------------

@pytest.fixture
def state_path(tmp_path, monkeypatch):
    """Redirect STATE_PATH to a tmp file for profile tests."""
    sp_file = tmp_path / "state.json"
    monkeypatch.setattr(web_ui_main, "STATE_PATH", str(sp_file))
    return sp_file


# ---------------------------------------------------------------------------
# POST /profile — PROF-01, PROF-02 (Phase 16)
# ---------------------------------------------------------------------------

def test_post_profile_valid(client, state_path):
    """POST /profile with valid key saves to state.json and returns 200 (PROF-02)."""
    resp = client.post("/profile", json={"profile": "kids_present"})
    assert resp.status_code == 200
    assert resp.json() == {"active_profile": "kids_present"}
    data = json.loads(state_path.read_text())
    assert data["active_profile"] == "kids_present"


def test_post_profile_invalid(client, state_path):
    """POST /profile with unknown profile key returns 400 (PROF-02)."""
    resp = client.post("/profile", json={"profile": "not_a_real_profile"})
    assert resp.status_code == 400


def test_post_profile_does_not_change_fsm(client, state_path):
    """POST /profile must not modify family_safe_mode (independence invariant, D-09)."""
    # Pre-seed state.json with family_safe_mode = True
    state_path.write_text(json.dumps({"family_safe_mode": True, "last_track_id": None}))
    resp = client.post("/profile", json={"profile": "were_all_adults"})
    assert resp.status_code == 200
    data = json.loads(state_path.read_text())
    assert data["family_safe_mode"] is True
    assert data["active_profile"] == "were_all_adults"


def test_dashboard_injects_profile_initial(client, state_path):
    """GET / replaces __PROFILE_INITIAL__ with active_profile from state.json (PROF-04)."""
    state_path.write_text(json.dumps({"family_safe_mode": False, "active_profile": "permissive"}))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "__PROFILE_INITIAL__" not in resp.text
    assert "permissive" in resp.text
