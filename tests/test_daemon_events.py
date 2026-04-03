"""Tests for Phase 6 daemon SSE event emission (DAEM-01, DAEM-02, DAEM-03)."""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import pytest_asyncio

import daemon


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect EVENTS_PATH and NOW_PLAYING_PATH to a tmp directory."""
    events_file = tmp_path / "events.jsonl"
    now_playing_file = tmp_path / "now_playing.json"
    monkeypatch.setattr(daemon, "EVENTS_PATH", str(events_file))
    monkeypatch.setattr(daemon, "NOW_PLAYING_PATH", str(now_playing_file))
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_track(track_id="spotify:track:abc123", name="Test Song",
                artist="Test Artist", explicit=False,
                images=None):
    if images is None:
        images = [{"url": "https://i.scdn.co/image/abc", "width": 640, "height": 640}]
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": artist}],
        "explicit": explicit,
        "album": {"images": images},
    }


def _mock_sp(track):
    sp = MagicMock()
    sp.current_playback.return_value = {
        "item": track,
        "device": {"name": "TestDevice", "id": "dev1", "is_restricted": False},
    }
    return sp


async def _run_one_cycle(sp, checker, state_override=None):
    """Run poll_loop for exactly one track-detection cycle."""
    state = {"last_track_id": None, "family_safe_mode": True, "consecutive_skips": 0}
    if state_override:
        state.update(state_override)

    soco_skip = AsyncMock()
    spotify_skip = AsyncMock()
    soco_skip.skip.return_value = True
    soco_skip.pause.return_value = True
    spotify_skip.skip.return_value = True

    # stop_event fires after one sleep cycle
    daemon.stop_event.clear()

    call_count = 0
    original_sleep = asyncio.sleep

    async def _one_shot_sleep(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            daemon.stop_event.set()
        await original_sleep(0)

    with patch("daemon.load_state", side_effect=[state, state]):
        with patch("daemon.save_state"):
            with patch("asyncio.sleep", side_effect=_one_shot_sleep):
                await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-01 implementation pending")
async def test_track_change_emitted_before_check(data_dir):
    """track_change must be written to events.jsonl BEFORE check() is called."""
    check_called_before = []

    async def _check_spy(track):
        check_called_before.append(
            (data_dir / "events.jsonl").read_text()
            if (data_dir / "events.jsonl").exists()
            else ""
        )
        return ("allow", "clean", 0)

    checker = MagicMock()
    checker.check = _check_spy
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)
    assert len(check_called_before) == 1
    events_before_check = check_called_before[0]
    lines = [json.loads(l) for l in events_before_check.strip().splitlines() if l.strip()]
    track_change_lines = [l for l in lines if l.get("type") == "track_change"]
    assert len(track_change_lines) >= 1, "track_change must be written before check() is called"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-01 implementation pending")
async def test_track_change_schema(data_dir):
    """track_change line must contain all required fields with correct values."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("allow", "clean", 0))
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists(), "events.jsonl must be created"
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    track_change_lines = [l for l in lines if l.get("type") == "track_change"]
    assert len(track_change_lines) >= 1, "At least one track_change event expected"

    evt = track_change_lines[0]
    assert evt["type"] == "track_change"
    assert evt["track_id"] == "spotify:track:abc123"
    assert evt["track"] == "Test Song"
    assert evt["artist"] == "Test Artist"
    assert evt["album_art_url"] == "https://i.scdn.co/image/abc"
    assert evt["eval_state"] == "evaluating"
    # timestamp must be HH:MM:SS format (8 chars, colons at positions 2 and 5)
    ts = evt["timestamp"]
    assert len(ts) == 8 and ts[2] == ":" and ts[5] == ":", f"timestamp {ts!r} not in HH:MM:SS format"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-02 implementation pending")
async def test_eval_result_passed(data_dir):
    """eval_result with eval_state='passed' emitted after check() returns allow/clean."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("allow", "clean", 0))
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1, "eval_result must be emitted after check()"
    assert eval_result_lines[0]["eval_state"] == "passed"
    assert eval_result_lines[0]["track_id"] == "spotify:track:abc123"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-02 implementation pending")
async def test_eval_result_skipped(data_dir):
    """eval_result with eval_state='skipped' emitted after check() returns skip/explicit."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("skip", "explicit", 3))
    track = _make_track(explicit=True)
    sp = _mock_sp(track)

    soco_skip = AsyncMock()
    soco_skip.skip.return_value = True
    soco_skip.pause.return_value = True
    spotify_skip = AsyncMock()
    spotify_skip.skip.return_value = True

    daemon.stop_event.clear()
    call_count = 0
    original_sleep = asyncio.sleep

    async def _one_shot_sleep(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            daemon.stop_event.set()
        await original_sleep(0)

    state = {"last_track_id": None, "family_safe_mode": True, "consecutive_skips": 0}
    with patch("daemon.load_state", side_effect=[state, state]):
        with patch("daemon.save_state"):
            with patch("asyncio.sleep", side_effect=_one_shot_sleep):
                await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1, "eval_result must be emitted after skip"
    assert eval_result_lines[0]["eval_state"] == "skipped"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-02 implementation pending")
async def test_eval_result_fsm_off(data_dir):
    """eval_result with eval_state='fsm-off' emitted even when family_safe_mode=False."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("allow", "clean", 0))
    track = _make_track()
    sp = _mock_sp(track)
    # FSM is off
    await _run_one_cycle(sp, checker, state_override={"family_safe_mode": False})

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1, "eval_result must be emitted even when FSM is off"
    assert eval_result_lines[0]["eval_state"] == "fsm-off"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-02 implementation pending")
async def test_eval_result_not_emitted_on_skip_failure(data_dir):
    """eval_result must NOT be written when skip() returns False."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("skip", "explicit", 3))
    track = _make_track(explicit=True)
    sp = _mock_sp(track)

    soco_skip = AsyncMock()
    soco_skip.skip.return_value = False
    soco_skip.pause.return_value = False
    spotify_skip = AsyncMock()
    spotify_skip.skip.return_value = False

    daemon.stop_event.clear()
    call_count = 0
    original_sleep = asyncio.sleep

    async def _one_shot_sleep(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            daemon.stop_event.set()
        await original_sleep(0)

    state = {"last_track_id": None, "family_safe_mode": True, "consecutive_skips": 0}
    with patch("daemon.load_state", side_effect=[state, state]):
        with patch("daemon.save_state"):
            with patch("asyncio.sleep", side_effect=_one_shot_sleep):
                await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    if not events_file.exists():
        return  # No events written at all — acceptable; no eval_result
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) == 0, "eval_result must NOT be emitted when skip fails"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-03 implementation pending")
async def test_now_playing_evaluating(data_dir):
    """now_playing.json must be written with eval_state='evaluating' BEFORE check() runs."""
    now_playing_snapshots = []

    async def _check_spy(track):
        np_file = data_dir / "now_playing.json"
        now_playing_snapshots.append(
            json.loads(np_file.read_text()) if np_file.exists() else None
        )
        return ("allow", "clean", 0)

    checker = MagicMock()
    checker.check = _check_spy
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)

    assert len(now_playing_snapshots) == 1, "check() must have been called once"
    snap = now_playing_snapshots[0]
    assert snap is not None, "now_playing.json must exist before check() is called"
    assert snap["eval_state"] == "evaluating"
    assert snap["track_id"] == "spotify:track:abc123"
    assert snap["track"] == "Test Song"
    assert snap["artist"] == "Test Artist"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="DAEM-03 implementation pending")
async def test_now_playing_final_state(data_dir):
    """now_playing.json must be overwritten with final eval_state after check() completes."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("allow", "clean", 0))
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)

    np_file = data_dir / "now_playing.json"
    assert np_file.exists(), "now_playing.json must be written"
    data = json.loads(np_file.read_text())
    # After evaluation with allow/clean, final state must be 'passed' (not 'evaluating')
    assert data["eval_state"] == "passed", (
        f"now_playing.json must have final eval_state='passed', got {data['eval_state']!r}"
    )
    assert data["track_id"] == "spotify:track:abc123"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=False, reason="D-01 regression — EVENTS_PATH rename pending")
async def test_existing_events_unaffected(data_dir):
    """After a skip cycle, events.jsonl must still contain a 'skip' event (D-01 regression)."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=("skip", "explicit", 3))
    track = _make_track(explicit=True)
    sp = _mock_sp(track)

    soco_skip = AsyncMock()
    soco_skip.skip.return_value = True
    soco_skip.pause.return_value = True
    spotify_skip = AsyncMock()
    spotify_skip.skip.return_value = True

    daemon.stop_event.clear()
    call_count = 0
    original_sleep = asyncio.sleep

    async def _one_shot_sleep(t):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            daemon.stop_event.set()
        await original_sleep(0)

    state = {"last_track_id": None, "family_safe_mode": True, "consecutive_skips": 0}
    with patch("daemon.load_state", side_effect=[state, state]):
        with patch("daemon.save_state"):
            with patch("asyncio.sleep", side_effect=_one_shot_sleep):
                await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists(), "events.jsonl must be created"
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    skip_lines = [l for l in lines if l.get("type") == "skip"]
    assert len(skip_lines) >= 1, (
        "events.jsonl must contain a 'skip' event — rename must not break existing event types"
    )
