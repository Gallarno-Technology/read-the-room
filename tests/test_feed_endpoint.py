"""Tests for GET /feed endpoint (HIST-03, Phase 15 Plan 01)."""
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
def events_path(tmp_path, monkeypatch):
    """Redirect EVENTS_PATH to a tmp file location."""
    ep = tmp_path / "events.jsonl"
    monkeypatch.setattr(web_ui_main, "EVENTS_PATH", str(ep))
    return ep


@pytest.fixture
def client(events_path):
    """TestClient with mocked sp (same pattern as test_web_ui_endpoints.py)."""
    mock_sp = MagicMock()
    monkeypatch_sp = patch.object(web_ui_main, "sp", mock_sp)
    with monkeypatch_sp:
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_feed_returns_recent_skips(client, events_path):
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
    events_path.write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    # newest-first: id=5 before id=4
    assert data[0]["id"] > data[1]["id"]
    assert data[0]["id"] == 5
    assert data[-1]["id"] == 1


def test_feed_filters_event_types(client, events_path):
    """GET /feed returns only skip and five_skip_warning events."""
    events = [
        {"id": 1, "type": "skip", "track": "A", "artist": "X", "reason": "explicit", "timestamp": "12:00:01"},
        {"id": 2, "type": "track_change", "track_id": "t1", "timestamp": "12:00:02"},
        {"id": 3, "type": "eval_result", "track_id": "t1", "eval_state": "passed", "timestamp": "12:00:03"},
        {"id": 4, "type": "idle", "timestamp": "12:00:04"},
        {"id": 5, "type": "five_skip_warning", "timestamp": "12:00:05"},
    ]
    events_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    types = {e["type"] for e in data}
    assert types == {"skip", "five_skip_warning"}


def test_feed_caps_at_20(client, events_path):
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
    events_path.write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 20
    # Most recent 20 means ids 30..11
    assert data[0]["id"] == 30
    assert data[-1]["id"] == 11


def test_feed_empty_file(client, events_path):
    """GET /feed when events.jsonl does not exist returns empty JSON array."""
    # events_path not created — file does not exist
    resp = client.get("/feed")
    assert resp.status_code == 200
    assert resp.json() == []


def test_feed_malformed_lines(client, events_path):
    """GET /feed skips malformed JSON lines without error."""
    lines = [
        json.dumps({"id": 1, "type": "skip", "track": "Good1", "artist": "A", "reason": "explicit", "timestamp": "12:00:01"}),
        "not json{",
        json.dumps({"id": 3, "type": "skip", "track": "Good2", "artist": "B", "reason": "explicit", "timestamp": "12:00:03"}),
    ]
    events_path.write_text("\n".join(lines) + "\n")

    resp = client.get("/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
