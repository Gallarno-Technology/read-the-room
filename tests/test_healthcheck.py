"""Tests for Docker healthcheck mechanism — DEPL-04.

Covers:
  test_poll_loop_touches_healthcheck_file: daemon touches /app/.healthcheck each poll cycle
  test_healthcheck_cmd_detects_stale_file: healthcheck CMD fails on stale file, passes on fresh
"""
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# DEPL-04: poll_loop() touches healthcheck file each iteration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_poll_loop_touches_healthcheck_file(tmp_path):
    """poll_loop() creates/touches /app/.healthcheck on each poll cycle.

    We redirect the touch to a tmp file to avoid needing /app at test time.
    """
    hc_file = tmp_path / ".healthcheck"

    # Mock all external dependencies so poll_loop runs one clean iteration
    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = None  # simulates nothing playing

    mock_content_checker = MagicMock()
    mock_soco_skip = MagicMock()
    mock_spotify_skip = MagicMock()

    import asyncio
    from daemon import stop_event, poll_loop

    stop_event.clear()

    # Patch Path('/app/.healthcheck') to point to our tmp file
    with patch("daemon.Path") as mock_path_cls:
        mock_path_instance = MagicMock()
        mock_path_cls.return_value = mock_path_instance

        # After first iteration, set stop_event to break the loop
        call_count = 0
        original_touch = mock_path_instance.touch

        def touch_and_stop():
            nonlocal call_count
            hc_file.touch()  # actually create the file in tmp_path
            call_count += 1
            stop_event.set()  # stop after first iteration

        mock_path_instance.touch.side_effect = touch_and_stop

        await poll_loop(mock_sp, mock_content_checker, mock_soco_skip, mock_spotify_skip)

    assert hc_file.exists(), "poll_loop() must touch the healthcheck file each iteration"
    stop_event.clear()  # reset for other tests


# ---------------------------------------------------------------------------
# DEPL-04: healthcheck CMD detects stale file (mtime > 60s ago)
# ---------------------------------------------------------------------------

def test_healthcheck_cmd_detects_stale_file(tmp_path):
    """The healthcheck CMD assertion fails if the file mtime is older than 60 seconds."""
    hc_file = tmp_path / ".healthcheck"
    hc_file.touch()

    # Backdate mtime to 120 seconds ago
    stale_time = time.time() - 120
    os.utime(str(hc_file), (stale_time, stale_time))

    # Replicate the CMD assertion: assert time.time() - os.stat(f).st_mtime < 60
    f = str(hc_file)
    with pytest.raises(AssertionError):
        assert time.time() - os.stat(f).st_mtime < 60


def test_healthcheck_cmd_passes_on_fresh_file(tmp_path):
    """The healthcheck CMD assertion passes if the file was touched recently."""
    hc_file = tmp_path / ".healthcheck"
    hc_file.touch()  # mtime = now

    f = str(hc_file)
    # Should NOT raise — file is fresh
    assert time.time() - os.stat(f).st_mtime < 60
