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
    monkeypatch_sp = patch.object(web_ui_main, "sp", mock_sp)
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
    """Returns HTTP 503 with skip_failed detail when sp.next_track() raises (D-05)."""
    import spotipy
    client._mock_sp.next_track.side_effect = spotipy.SpotifyException(
        http_status=403, code=-1, msg="No active device"
    )
    resp = client.post("/skip")
    assert resp.status_code == 503
    body = resp.json()
    assert body["detail"] == "skip_failed"
    assert "No active device" in body["reason"]
