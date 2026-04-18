"""Tests for GET /feed endpoint (HIST-03, Phase 15 Plan 01).

Updated in Phase 28 to use mock_ctx fixture instead of EVENTS_PATH monkeypatching.
"""
import json
import os
import pathlib
import sys
import pytest
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
    uid = "feedtestuid"
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
    return UserContext(
        uid="feedtestuid",
        state_path=str(user_dir / "state.json"),
        events_path=str(user_dir / "data" / "events.jsonl"),
        now_playing_path=str(user_dir / "data" / "now_playing.json"),
        token_cache_path=str(user_dir / "token_cache" / ".cache"),
    )


@pytest.fixture
def client(mock_ctx):
    """TestClient that overrides get_user_context with mock_ctx."""
    mock_sp = MagicMock()
    web_ui_main.app.dependency_overrides[web_ui_main.get_user_context] = lambda: mock_ctx
    with patch.object(web_ui_main, "_sp_init", return_value=mock_sp):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            yield c
    web_ui_main.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_feed_returns_recent_skips(client, mock_ctx):
    """GET /feed with 5 skip events returns all 5 as JSON array, newest-first."""
    lines = []
    for i in range(1, 6):
        lines.append(json.dumps({
            "id": i,
            "type": "skip",
            "track": f"Track {i}",
            "artist": f"Artist {i}",
            "reason": "explicit",
            "timestamp": f"12:00:0{i}",
        }))
    pathlib.Path(mock_ctx.events_path).write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    # newest-first: id=5 before id=4
    assert data[0]["id"] > data[1]["id"]
    assert data[0]["id"] == 5
    assert data[-1]["id"] == 1


def test_feed_filters_event_types(client, mock_ctx):
    """GET /feed returns only skip and five_skip_warning events."""
    events = [
        {"id": 1, "type": "skip", "track": "A", "artist": "X", "reason": "explicit", "timestamp": "12:00:01"},
        {"id": 2, "type": "track_change", "track_id": "t1", "timestamp": "12:00:02"},
        {"id": 3, "type": "eval_result", "track_id": "t1", "eval_state": "passed", "timestamp": "12:00:03"},
        {"id": 4, "type": "idle", "timestamp": "12:00:04"},
        {"id": 5, "type": "five_skip_warning", "timestamp": "12:00:05"},
    ]
    pathlib.Path(mock_ctx.events_path).write_text("\n".join(json.dumps(e) for e in events) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    types = {e["type"] for e in data}
    assert types == {"skip", "five_skip_warning"}


def test_feed_caps_at_20(client, mock_ctx):
    """GET /feed with 30 skip events returns only the 20 most recent."""
    lines = []
    for i in range(1, 31):
        lines.append(json.dumps({
            "id": i,
            "type": "skip",
            "track": f"Track {i}",
            "artist": f"Artist {i}",
            "reason": "explicit",
            "timestamp": f"12:{i:02d}:00",
        }))
    pathlib.Path(mock_ctx.events_path).write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 20
    # Most recent 20 means ids 30..11
    assert data[0]["id"] == 30
    assert data[-1]["id"] == 11


def test_feed_empty_file(client, mock_ctx):
    """GET /feed when events.jsonl does not exist returns empty JSON array."""
    # Remove the file so it does not exist
    pathlib.Path(mock_ctx.events_path).unlink()
    resp = client.get("/feed")
    assert resp.status_code == 200
    assert resp.json() == []


def test_feed_malformed_lines(client, mock_ctx):
    """GET /feed skips malformed JSON lines without error."""
    lines = [
        json.dumps({"id": 1, "type": "skip", "track": "Good1", "artist": "A", "reason": "explicit", "timestamp": "12:00:01"}),
        "not json{",
        json.dumps({"id": 3, "type": "skip", "track": "Good2", "artist": "B", "reason": "explicit", "timestamp": "12:00:03"}),
    ]
    pathlib.Path(mock_ctx.events_path).write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
