"""Tests for Phase 6 daemon SSE event emission (DAEM-01, DAEM-02, DAEM-03)."""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import pytest_asyncio

import daemon
from content_checker import TrackEvalResult
from spotipy.exceptions import SpotifyException


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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)


async def _run_n_empty_cycles(n: int, data_dir, resume_on=None, resume_track=None):
    """Run poll_loop for N cycles where current_playback returns None.

    If resume_on is set, cycle at that index returns resume_track instead of None.
    """
    state = {"last_track_id": None, "family_safe_mode": False, "consecutive_skips": 0}
    soco_skip = AsyncMock()
    spotify_skip = AsyncMock()
    soco_skip.skip.return_value = True
    soco_skip.pause.return_value = True
    spotify_skip.skip.return_value = True

    daemon.stop_event.clear()

    cycle_count = 0
    original_sleep = asyncio.sleep

    async def _n_shot_sleep(t):
        nonlocal cycle_count
        cycle_count += 1
        if cycle_count >= n:
            daemon.stop_event.set()
        await original_sleep(0)

    sp = MagicMock()
    playback_call = 0

    def _playback():
        nonlocal playback_call
        idx = playback_call
        playback_call += 1
        if resume_on is not None and idx == resume_on:
            return {"item": resume_track, "device": {"name": "Dev", "id": "d1", "is_restricted": False}}
        return None

    sp.current_playback.side_effect = _playback
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))

    with patch("daemon.load_state", return_value=state):
        with patch("daemon.save_state"):
            with patch("asyncio.sleep", side_effect=_n_shot_sleep):
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_track_change_emitted_before_check(data_dir):
    """track_change must be written to events.jsonl BEFORE check() is called."""
    check_called_before = []

    async def _check_spy(track):
        check_called_before.append(
            (data_dir / "events.jsonl").read_text()
            if (data_dir / "events.jsonl").exists()
            else ""
        )
        return TrackEvalResult(action="allow", reason="clean", severity=0)

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
async def test_track_change_schema(data_dir):
    """track_change line must contain all required fields with correct values."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
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
async def test_eval_result_passed(data_dir):
    """eval_result with eval_state='passed' emitted after check() returns allow/clean."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
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
    assert eval_result_lines[0]["severity"] == 0
    assert eval_result_lines[0]["drug_reference"] == False
    assert eval_result_lines[0]["sexual_content"] == False
    assert eval_result_lines[0]["explicit"] == False
    assert eval_result_lines[0]["profanity"] == False


@pytest.mark.asyncio
async def test_eval_result_skipped(data_dir):
    """eval_result with eval_state='skipped' emitted after check() returns skip/explicit."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True))
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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1, "eval_result must be emitted after skip"
    assert eval_result_lines[0]["eval_state"] == "skipped"
    assert eval_result_lines[0]["severity"] == 3
    assert eval_result_lines[0]["explicit"] == True
    assert eval_result_lines[0]["profanity"] == False
    assert eval_result_lines[0]["drug_reference"] == False
    assert eval_result_lines[0]["sexual_content"] == False


@pytest.mark.asyncio
async def test_eval_result_fsm_off(data_dir):
    """eval_result with eval_state='fsm-off' emitted even when family_safe_mode=False."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
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
    assert eval_result_lines[0]["severity"] == 0
    assert eval_result_lines[0]["explicit"] == False
    assert eval_result_lines[0]["profanity"] == False
    assert eval_result_lines[0]["drug_reference"] == False
    assert eval_result_lines[0]["sexual_content"] == False


@pytest.mark.asyncio
async def test_eval_result_not_emitted_on_skip_failure(data_dir):
    """eval_result must NOT be written when skip() returns False."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="skip", reason="explicit", severity=3))
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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    if not events_file.exists():
        return  # No events written at all — acceptable; no eval_result
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) == 0, "eval_result must NOT be emitted when skip fails"


@pytest.mark.asyncio
async def test_now_playing_evaluating(data_dir):
    """now_playing.json must be written with eval_state='evaluating' BEFORE check() runs."""
    now_playing_snapshots = []

    async def _check_spy(track):
        np_file = data_dir / "now_playing.json"
        now_playing_snapshots.append(
            json.loads(np_file.read_text()) if np_file.exists() else None
        )
        return TrackEvalResult(action="allow", reason="clean", severity=0)

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
async def test_now_playing_final_state(data_dir):
    """now_playing.json must be overwritten with final eval_state after check() completes."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
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
    assert "drug_reference" in data, "now_playing.json must carry drug_reference field (D-10)"
    assert "sexual_content" in data, "now_playing.json must carry sexual_content field (D-10)"
    assert "explicit" in data, "now_playing.json must carry explicit field (D-10)"
    assert "profanity" in data, "now_playing.json must carry profanity field (D-10)"
    assert data["drug_reference"] == False
    assert data["sexual_content"] == False
    assert data["explicit"] == False
    assert data["profanity"] == False


@pytest.mark.asyncio
async def test_existing_events_unaffected(data_dir):
    """After a skip cycle, events.jsonl must still contain a 'skip' event (D-01 regression)."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="skip", reason="explicit", severity=3))
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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists(), "events.jsonl must be created"
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    skip_lines = [l for l in lines if l.get("type") == "skip"]
    assert len(skip_lines) >= 1, (
        "events.jsonl must contain a 'skip' event — rename must not break existing event types"
    )


@pytest.mark.asyncio
async def test_skip_event_includes_four_booleans(data_dir):
    """skip event in events.jsonl must carry all four boolean fields (LOG-01 / D-07)."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(
        action="skip", reason="explicit", severity=3, explicit=True
    ))
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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    skip_lines = [l for l in lines if l.get("type") == "skip"]
    assert len(skip_lines) >= 1, "events.jsonl must contain a skip event"
    skip = skip_lines[0]
    assert "explicit" in skip, "skip event must have explicit field (LOG-01)"
    assert "profanity" in skip, "skip event must have profanity field (LOG-01)"
    assert "drug_reference" in skip, "skip event must have drug_reference field (LOG-01)"
    assert "sexual_content" in skip, "skip event must have sexual_content field (LOG-01)"
    assert skip["explicit"] == True
    assert skip["profanity"] == False
    assert skip["drug_reference"] == False
    assert skip["sexual_content"] == False


@pytest.mark.asyncio
async def test_eval_result_drug_reference_boolean(data_dir):
    """eval_result event sets drug_reference=True when checker returns drug_reference reason (LOG-01)."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(
        action="skip", reason="drug_reference", severity=0,
        drug_reference=True
    ))
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
                with patch("pathlib.Path.touch"):
                    await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1
    assert eval_result_lines[0]["drug_reference"] == True
    assert eval_result_lines[0]["sexual_content"] == False
    assert eval_result_lines[0]["explicit"] == False
    assert eval_result_lines[0]["profanity"] == False


@pytest.mark.asyncio
async def test_eval_result_severity_mild(data_dir):
    """eval_result includes severity=1 when checker returns mild profanity."""
    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="mild_language", severity=1))
    track = _make_track()
    sp = _mock_sp(track)
    await _run_one_cycle(sp, checker)

    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
    assert len(eval_result_lines) >= 1
    assert eval_result_lines[0]["severity"] == 1


# ---------------------------------------------------------------------------
# Idle-detection tests (IDLE-01, IDLE-02) — RED state; daemon has no idle logic yet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idle_writes_now_playing(data_dir):
    """After 3 consecutive empty polls, now_playing.json must contain {"status": "idle"}."""
    await _run_n_empty_cycles(4, data_dir)  # 4 cycles ensures threshold (3) is crossed
    np_file = data_dir / "now_playing.json"
    assert np_file.exists(), "now_playing.json must be written on idle"
    data = json.loads(np_file.read_text())
    assert data == {"status": "idle"}, f'Expected {{"status": "idle"}}, got {data}'


@pytest.mark.asyncio
async def test_idle_dedup(data_dir):
    """After 5 empty polls, now_playing.json written once and events.jsonl has exactly one idle event."""
    await _run_n_empty_cycles(6, data_dir)
    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    idle_lines = [
        json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()
        if json.loads(l).get("type") == "idle"
    ]
    assert len(idle_lines) == 1, f"Expected 1 idle event, got {len(idle_lines)}"


@pytest.mark.asyncio
async def test_idle_resets_on_track(data_dir):
    """3 empty -> 1 active -> 3 empty must produce 2 idle events total."""
    resume_track = _make_track(track_id="spotify:track:resume1")
    # First idle period: cycles 0-2 empty (threshold at 3), cycle 3 active (resets)
    # Second idle period: cycles 4-6 empty (threshold at 3 again = 2nd idle)
    await _run_n_empty_cycles(8, data_dir, resume_on=3, resume_track=resume_track)
    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    idle_events = [l for l in lines if l.get("type") == "idle"]
    assert len(idle_events) == 2, f"Expected 2 idle events (reset between periods), got {len(idle_events)}"


@pytest.mark.asyncio
async def test_idle_event_emitted(data_dir):
    """After 3 empty polls, events.jsonl must contain an idle event with timestamp field."""
    await _run_n_empty_cycles(4, data_dir)
    events_file = data_dir / "events.jsonl"
    assert events_file.exists(), "events.jsonl must be written"
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    idle_events = [l for l in lines if l.get("type") == "idle"]
    assert len(idle_events) >= 1, "At least one idle event must be in events.jsonl"
    evt = idle_events[0]
    assert "timestamp" in evt, "idle event must have a timestamp field"
    assert evt["type"] == "idle"


@pytest.mark.asyncio
async def test_event_id_added(data_dir):
    """Calling _append_event writes a JSON line containing an integer 'id' field."""
    daemon._event_counter = 0
    daemon._append_event({"type": "skip"})
    events_file = data_dir / "events.jsonl"
    assert events_file.exists()
    line = events_file.read_text().strip()
    evt = json.loads(line)
    assert "id" in evt, "Event must have an 'id' field"
    assert evt["id"] == 1
    assert isinstance(evt["id"], int)


@pytest.mark.asyncio
async def test_event_id_increments(data_dir):
    """Calling _append_event twice produces events with id=1 and id=2."""
    daemon._event_counter = 0
    daemon._append_event({"type": "skip"})
    daemon._append_event({"type": "skip"})
    events_file = data_dir / "events.jsonl"
    lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
    assert lines[0]["id"] == 1
    assert lines[1]["id"] == 2


@pytest.mark.asyncio
async def test_init_event_counter_from_file(data_dir):
    """_init_event_counter reads the last event's id and sets _event_counter."""
    events_file = data_dir / "events.jsonl"
    events_file.write_text(json.dumps({"id": 42, "type": "skip"}) + "\n")
    daemon._event_counter = 0
    daemon._init_event_counter()
    assert daemon._event_counter == 42


@pytest.mark.asyncio
async def test_init_event_counter_empty_file(data_dir):
    """_init_event_counter with missing file sets _event_counter to 0."""
    daemon._event_counter = 99
    daemon._init_event_counter()
    assert daemon._event_counter == 0


@pytest.mark.asyncio
async def test_idle_debounce(data_dir):
    """2 empty polls (below threshold of 3) must NOT write idle state or emit idle event."""
    await _run_n_empty_cycles(2, data_dir)
    np_file = data_dir / "now_playing.json"
    # now_playing.json should not exist (no idle write triggered)
    if np_file.exists():
        data = json.loads(np_file.read_text())
        assert data.get("status") != "idle", "idle must not be written after only 2 empty polls"
    events_file = data_dir / "events.jsonl"
    if events_file.exists():
        lines = [json.loads(l) for l in events_file.read_text().strip().splitlines() if l.strip()]
        idle_events = [l for l in lines if l.get("type") == "idle"]
        assert len(idle_events) == 0, f"No idle events expected after 2 polls, got {len(idle_events)}"


# ---------------------------------------------------------------------------
# Phase 30: Consecutive 401 counter — TDD RED scaffolds (D-01, D-02)
# These tests FAIL against unmodified codebase (no counter yet in daemon.py).
# ---------------------------------------------------------------------------

async def _drive_poll_loop_with_401s(
    n_401s: int,
    then_succeed: bool = False,
    more_401s_after: int = 0,
    data_dir=None,
):
    """Helper to drive poll_loop with a controlled sequence of 401 errors and successes.

    Args:
        n_401s: Number of consecutive SpotifyException(401) calls at start.
        then_succeed: If True, follow the 401s with one successful playback call.
        more_401s_after: After the success (if then_succeed), raise this many more 401s.
        data_dir: Optional tmp directory fixture for file paths.
    """
    soco_skip = AsyncMock()
    soco_skip.skip.return_value = True
    soco_skip.pause.return_value = True
    spotify_skip = AsyncMock()
    spotify_skip.skip.return_value = True

    checker = MagicMock()
    checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))

    daemon.stop_event.clear()

    call_count = [0]
    original_sleep = asyncio.sleep

    # Build the sequence of responses for sp.current_playback()
    responses = []
    for _ in range(n_401s):
        responses.append(SpotifyException(http_status=401, code=-1, msg="Unauthorized"))
    if then_succeed:
        # One successful playback call returns None (no track playing)
        responses.append(None)
        for _ in range(more_401s_after):
            responses.append(SpotifyException(http_status=401, code=-1, msg="Unauthorized"))

    # After all scripted responses, set stop_event so poll_loop exits cleanly
    total_calls = [0]
    def playback_side_effect():
        idx = total_calls[0]
        total_calls[0] += 1
        if idx < len(responses):
            val = responses[idx]
            if isinstance(val, Exception):
                raise val
            return val
        # Past the scripted calls — stop the loop
        daemon.stop_event.set()
        return None

    async def _controlled_sleep(t):
        call_count[0] += 1
        # Stop loop after all scripted calls exhausted (safety valve)
        if total_calls[0] >= len(responses):
            daemon.stop_event.set()
        await original_sleep(0)

    sp = MagicMock()
    sp.current_playback.side_effect = playback_side_effect

    state = {"last_track_id": None, "family_safe_mode": False, "consecutive_skips": 0}
    with patch("daemon.load_state", return_value=state), \
         patch("daemon.save_state"), \
         patch("asyncio.sleep", side_effect=_controlled_sleep), \
         patch("pathlib.Path.touch"):
        await daemon.poll_loop(sp, checker, soco_skip, spotify_skip)


@pytest.mark.asyncio
async def test_three_consecutive_401s_trigger_exit2(data_dir):
    """Three consecutive 401 errors cause sys.exit(2) (D-01).

    Fails against unmodified daemon.py: no consecutive counter exists.
    """
    with pytest.raises(SystemExit) as excinfo:
        await _drive_poll_loop_with_401s(n_401s=3, data_dir=data_dir)
    assert excinfo.value.code == 2, (
        f"Three consecutive 401s must trigger sys.exit(2); got code {excinfo.value.code}"
    )


@pytest.mark.asyncio
async def test_consecutive_401_counter_resets_on_success(data_dir):
    """Counter resets to 0 on success; 2 + success + 1 must NOT trigger exit(2) (D-02).

    Sequence: 401, 401, success, 401 → total consecutive at end is 1, not 3.
    Fails against unmodified daemon.py: no reset logic exists.
    """
    # This test should complete without SystemExit — if the counter is NOT reset,
    # only 2 consecutive 401s before success means it wouldn't reach 3 anyway.
    # To properly test reset: we need 2 + success + 2 = max consecutive is 2 < 3 (no exit).
    # If the counter does NOT reset: cumulative would be 4 after the final 401 — triggers exit.
    # So this tests that a success resets the counter.
    try:
        await _drive_poll_loop_with_401s(
            n_401s=2,
            then_succeed=True,
            more_401s_after=2,
            data_dir=data_dir,
        )
    except SystemExit as exc:
        pytest.fail(
            f"Counter must reset on success — sys.exit({exc.code}) triggered unexpectedly. "
            "With 2 + success + 2, max consecutive is 2 — no exit should occur."
        )


@pytest.mark.asyncio
async def test_single_401_does_not_exit(data_dir):
    """A single 401 followed by clean loop exit must NOT trigger sys.exit(2) (D-01 boundary).

    This test documents the contract that a single 401 is tolerated.
    """
    try:
        await _drive_poll_loop_with_401s(n_401s=1, data_dir=data_dir)
    except SystemExit as exc:
        pytest.fail(
            f"A single 401 must not trigger sys.exit(2); got sys.exit({exc.code})"
        )
