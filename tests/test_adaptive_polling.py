"""Tests for adaptive Spotify polling cadence — quick task 260504-jkb.

Covers:
  - _compute_next_sleep tier selection (active / idle / track-end accelerator)
  - POLL_INTERVAL_SECONDS deprecated single-tier override
  - poll_loop kick-file consumption (SSE-reconnect short-circuit)
  - poll_loop respects POLL_INTERVAL_ACTIVE on a normal (is_playing) iteration
"""
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# A. Pure-function tests for _compute_next_sleep
# ---------------------------------------------------------------------------

ACTIVE = 5.0
IDLE = 30.0
THRESHOLD_MS = 5000


def test_compute_next_sleep_returns_idle_when_result_is_none():
    from daemon import _compute_next_sleep
    assert _compute_next_sleep(None, ACTIVE, IDLE, THRESHOLD_MS) == IDLE


def test_compute_next_sleep_returns_idle_when_item_is_none():
    from daemon import _compute_next_sleep
    result = {"is_playing": True, "item": None, "progress_ms": 0}
    assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS) == IDLE


def test_compute_next_sleep_returns_idle_when_paused_mid_track():
    from daemon import _compute_next_sleep
    result = {
        "is_playing": False,
        "progress_ms": 100000,
        "item": {"id": "x", "duration_ms": 200000},
    }
    assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS) == IDLE


def test_compute_next_sleep_returns_active_when_playing_mid_track():
    from daemon import _compute_next_sleep
    result = {
        "is_playing": True,
        "progress_ms": 100000,
        "item": {"id": "x", "duration_ms": 200000},
    }
    assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS) == ACTIVE


def test_compute_next_sleep_returns_active_when_playing_near_track_end():
    """Track-end threshold path executes; result is still active (no-op tier change)."""
    from daemon import _compute_next_sleep
    result = {
        "is_playing": True,
        "progress_ms": 199000,  # 1s remaining, under 5000ms threshold
        "item": {"id": "x", "duration_ms": 200000},
    }
    assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS) == ACTIVE


def test_compute_next_sleep_accelerates_when_paused_near_track_end():
    """Paused-near-end: still poll active so we catch auto-advance / play-next."""
    from daemon import _compute_next_sleep
    result = {
        "is_playing": False,
        "progress_ms": 199000,  # 1s remaining, under threshold
        "item": {"id": "x", "duration_ms": 200000},
    }
    assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS) == ACTIVE


def test_compute_next_sleep_override_forces_single_tier_for_all_cases():
    """POLL_INTERVAL_SECONDS override: returns the override value regardless of state."""
    from daemon import _compute_next_sleep
    override = 2.0
    cases = [
        None,
        {"is_playing": True, "item": None, "progress_ms": 0},
        {"is_playing": False, "progress_ms": 100000,
         "item": {"id": "x", "duration_ms": 200000}},
        {"is_playing": True, "progress_ms": 100000,
         "item": {"id": "x", "duration_ms": 200000}},
        {"is_playing": True, "progress_ms": 199000,
         "item": {"id": "x", "duration_ms": 200000}},
        {"is_playing": False, "progress_ms": 199000,
         "item": {"id": "x", "duration_ms": 200000}},
    ]
    for result in cases:
        assert _compute_next_sleep(result, ACTIVE, IDLE, THRESHOLD_MS, override=override) == override


# ---------------------------------------------------------------------------
# B. poll_loop integration: active-tier sleep on a playing iteration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_poll_loop_uses_active_tier_when_playing(tmp_path, monkeypatch):
    """One iteration of poll_loop with is_playing=True selects POLL_INTERVAL_ACTIVE."""
    import daemon

    # Redirect state file to tmp_path so kick path resolves under tmp_path
    monkeypatch.setattr(daemon, "STATE_PATH", str(tmp_path / "state.json"))
    # Force adaptive path even if local .env sets the deprecated override.
    monkeypatch.setattr(daemon, "_POLL_INTERVAL_OVERRIDE", 0.0)
    # Redirect now_playing/events writes into tmp_path too.
    monkeypatch.setattr(daemon, "EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setattr(daemon, "NOW_PLAYING_PATH", str(tmp_path / "now_playing.json"))

    mock_sp = MagicMock()
    mock_sp.currently_playing.return_value = {
        "is_playing": True,
        "progress_ms": 1000,
        "item": {
            "id": "trackA",
            "name": "Song A",
            "explicit": False,
            "duration_ms": 200000,
            "artists": [{"name": "Artist A"}],
            "album": {"images": []},
        },
        "device": {"name": "TestDevice", "is_restricted": False, "id": "devA"},
    }

    daemon.stop_event.clear()
    captured_sleeps: list[float] = []

    async def fake_sleep(t):
        # Capture the sleep duration (== next_sleep), then trigger stop_event.
        captured_sleeps.append(t)
        daemon.stop_event.set()

    with patch("daemon.Path") as mock_path_cls, \
         patch("asyncio.sleep", side_effect=fake_sleep):
        mock_path_cls.return_value = MagicMock()
        await daemon.poll_loop(
            mock_sp,
            MagicMock(),  # content_checker (not exercised — FSM is off by default)
            MagicMock(),  # soco_skip
            MagicMock(),  # spotify_skip
        )

    daemon.stop_event.clear()
    assert captured_sleeps, "poll_loop must call asyncio.sleep at the bottom of each iteration"
    assert captured_sleeps[0] == daemon.POLL_INTERVAL_ACTIVE


# ---------------------------------------------------------------------------
# C. Kick-file consumption inside poll_loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_poll_loop_consumes_kick_file_and_short_circuits(tmp_path, monkeypatch):
    """A pre-existing poll_kick file is removed and the bottom-of-loop sleep is bypassed.

    Implementation contract: when the kick file exists, next_sleep is forced to 0
    and the interruptible asyncio.wait_for is skipped (no sleep at all). The next
    iteration polls Spotify immediately.
    """
    import daemon

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(daemon, "STATE_PATH", str(state_path))
    monkeypatch.setattr(daemon, "_POLL_INTERVAL_OVERRIDE", 0.0)
    monkeypatch.setattr(daemon, "EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setattr(daemon, "NOW_PLAYING_PATH", str(tmp_path / "now_playing.json"))
    kick_path = tmp_path / "poll_kick"
    kick_path.touch()
    assert kick_path.exists()

    mock_sp = MagicMock()
    # Idle response — would normally choose IDLE tier
    mock_sp.currently_playing.return_value = None

    daemon.stop_event.clear()
    captured_sleeps: list[float] = []
    poll_count = {"n": 0}

    # Stop the loop on the SECOND poll call so we observe the kick-consume iteration
    # AND confirm the next iteration was reached without going through the idle wait.
    def stopping_currently_playing():
        poll_count["n"] += 1
        if poll_count["n"] >= 2:
            daemon.stop_event.set()
        return None

    mock_sp.currently_playing.side_effect = stopping_currently_playing

    async def fake_sleep(t):
        captured_sleeps.append(t)

    with patch("daemon.Path") as mock_path_cls, \
         patch("asyncio.sleep", side_effect=fake_sleep):
        mock_path_cls.return_value = MagicMock()
        await daemon.poll_loop(mock_sp, MagicMock(), MagicMock(), MagicMock())

    daemon.stop_event.clear()
    assert not kick_path.exists(), "poll_loop must unlink poll_kick after consuming it"
    assert poll_count["n"] >= 2, "loop must reach a second iteration without sleeping after kick consume"
    # Iteration 1 (kick consumed): next_sleep=0 -> sleep skipped entirely.
    # Iteration 2 (no kick): IDLE tier -> asyncio.sleep(30).
    # So captured_sleeps must contain exactly the IDLE-tier sleep from iteration 2.
    assert captured_sleeps == [daemon.POLL_INTERVAL_IDLE], (
        f"Expected only an IDLE sleep on the second iteration, got {captured_sleeps}. "
        "If a 0.0 appears before IDLE, the implementation called asyncio.sleep(0) "
        "instead of skipping the sleep entirely — both forms are semantically "
        "equivalent but the spec says skip."
    )


@pytest.mark.asyncio
async def test_poll_loop_no_kick_file_is_noop(tmp_path, monkeypatch):
    """Missing kick file does not raise and does not affect the chosen tier."""
    import daemon

    monkeypatch.setattr(daemon, "STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(daemon, "_POLL_INTERVAL_OVERRIDE", 0.0)
    monkeypatch.setattr(daemon, "EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setattr(daemon, "NOW_PLAYING_PATH", str(tmp_path / "now_playing.json"))
    # Ensure no kick file
    kick_path = tmp_path / "poll_kick"
    assert not kick_path.exists()

    mock_sp = MagicMock()
    mock_sp.currently_playing.return_value = None  # idle

    daemon.stop_event.clear()
    captured_sleeps: list[float] = []

    async def fake_sleep(t):
        captured_sleeps.append(t)
        daemon.stop_event.set()

    with patch("daemon.Path") as mock_path_cls, \
         patch("asyncio.sleep", side_effect=fake_sleep):
        mock_path_cls.return_value = MagicMock()
        await daemon.poll_loop(mock_sp, MagicMock(), MagicMock(), MagicMock())

    daemon.stop_event.clear()
    # Idle response with no kick: must pick IDLE tier
    assert captured_sleeps and captured_sleeps[0] == daemon.POLL_INTERVAL_IDLE
