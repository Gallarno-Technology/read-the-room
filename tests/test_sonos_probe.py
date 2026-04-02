"""Tests for probe_sonos_speakers() in daemon.py — TDD RED phase for Plan 04-01.

These tests will FAIL until Plan 04-02 implements probe_sonos_speakers in daemon.py.

Behaviors tested:
  DISC-01: probe calls soco.discovery.discover when SONOS_SPEAKER_IPS is not set
  DISC-01: probe logs discovered speakers as '[SONOS] Discovered: "Name" (IP)'
  DISC-01/DISC-02: probe pre-seeds SocoSkipClient._ip_cache from discovered speakers
  DISC-02: probe skips SSDP and logs override message when SONOS_SPEAKER_IPS is set
  DISC-03: probe logs actionable warning (with multicast/port/env hint) when no speakers found
"""
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from skip_client import SocoSkipClient


# ---------------------------------------------------------------------------
# DISC-01: SSDP discovery path (SONOS_SPEAKER_IPS not set)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_probe_calls_ssdp_when_no_ip_override():
    """probe_sonos_speakers calls soco.discovery.discover when SONOS_SPEAKER_IPS is unset."""
    from daemon import probe_sonos_speakers

    soco_client = SocoSkipClient()

    with patch("daemon.soco.discovery.discover", return_value=set()) as mock_discover, \
         patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SONOS_SPEAKER_IPS", None)
        await probe_sonos_speakers(soco_client)

    mock_discover.assert_called_once()


@pytest.mark.asyncio
async def test_probe_logs_discovered_speakers(caplog):
    """probe_sonos_speakers logs '[SONOS] Discovered: "Name" (IP)' for each found speaker (D-05)."""
    from daemon import probe_sonos_speakers

    mock_speaker = MagicMock()
    mock_speaker.player_name = "Living Room"
    mock_speaker.ip_address = "192.168.1.164"

    soco_client = SocoSkipClient()

    with patch("daemon.soco.discovery.discover", return_value={mock_speaker}), \
         patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SONOS_SPEAKER_IPS", None)
        with caplog.at_level(logging.INFO, logger="daemon"):
            await probe_sonos_speakers(soco_client)

    assert any(
        '[SONOS] Discovered: "Living Room" (192.168.1.164)' in record.message
        for record in caplog.records
    ), f"Expected discovery log line not found. Records: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_probe_seeds_ip_cache():
    """probe_sonos_speakers pre-seeds SocoSkipClient._ip_cache from discovered speakers."""
    from daemon import probe_sonos_speakers

    mock_speaker = MagicMock()
    mock_speaker.player_name = "Living Room"
    mock_speaker.ip_address = "192.168.1.164"

    with patch("daemon.soco.discovery.discover", return_value={mock_speaker}), \
         patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SONOS_SPEAKER_IPS", None)
        # Create SocoSkipClient AFTER clearing SONOS_SPEAKER_IPS so constructor
        # does not pre-seed _ip_cache from the real .env value.
        soco_client = SocoSkipClient()
        assert "Living Room" not in soco_client._ip_cache

        await probe_sonos_speakers(soco_client)

    assert soco_client._ip_cache.get("Living Room") == "192.168.1.164", (
        f"Expected _ip_cache['Living Room'] == '192.168.1.164', got {soco_client._ip_cache}"
    )


# ---------------------------------------------------------------------------
# DISC-02: IP override path (SONOS_SPEAKER_IPS is set)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_probe_skips_ssdp_when_ip_override_set():
    """probe_sonos_speakers does NOT call soco.discovery.discover when SONOS_SPEAKER_IPS is set (D-02)."""
    from daemon import probe_sonos_speakers

    soco_client = SocoSkipClient()

    with patch("daemon.soco.discovery.discover") as mock_discover, \
         patch.dict(os.environ, {"SONOS_SPEAKER_IPS": "Living Room=192.168.1.164"}):
        await probe_sonos_speakers(soco_client)

    mock_discover.assert_not_called()


@pytest.mark.asyncio
async def test_probe_logs_ip_override_active(caplog):
    """probe_sonos_speakers logs '[SONOS] IP override active' when SONOS_SPEAKER_IPS is set (D-02)."""
    from daemon import probe_sonos_speakers

    soco_client = SocoSkipClient()

    with patch("daemon.soco.discovery.discover"), \
         patch.dict(os.environ, {"SONOS_SPEAKER_IPS": "Living Room=192.168.1.164"}):
        with caplog.at_level(logging.INFO, logger="daemon"):
            await probe_sonos_speakers(soco_client)

    assert any(
        "[SONOS] IP override active" in record.message
        for record in caplog.records
    ), f"Expected IP override log not found. Records: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# DISC-03: Failure / actionable warning path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_probe_logs_actionable_warning_when_no_speakers_found(caplog):
    """probe_sonos_speakers logs WARNING with port 1900 hint and env var hint when no speakers found (D-07)."""
    from daemon import probe_sonos_speakers

    soco_client = SocoSkipClient()

    # discover() returns None on many SoCo versions when no speakers found
    with patch("daemon.soco.discovery.discover", return_value=None), \
         patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SONOS_SPEAKER_IPS", None)
        with caplog.at_level(logging.WARNING, logger="daemon"):
            await probe_sonos_speakers(soco_client)

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_messages, "Expected at least one WARNING log when no speakers found"
    combined = " ".join(warning_messages)
    assert "multicast UDP port 1900" in combined, (
        f"WARNING must mention 'multicast UDP port 1900'. Got: {combined}"
    )
    assert "SONOS_SPEAKER_IPS" in combined, (
        f"WARNING must mention 'SONOS_SPEAKER_IPS'. Got: {combined}"
    )
