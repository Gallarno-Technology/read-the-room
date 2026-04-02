"""Tests for SkipClient pause() method — TDD for Plan 03-05.

Tests:
1. SpotifySkipClient.pause calls sp.pause_playback(device_id) via run_in_executor, returns True
2. SpotifySkipClient.pause returns False and logs error on SpotifyException
3. SocoSkipClient.pause calls speaker.pause() via run_in_executor using cached IP, returns True
4. SocoSkipClient.pause falls back to discovery when IP not cached, returns True
5. SocoSkipClient.pause returns False and logs warning if speaker not found
6. SkipClient ABC exposes pause() as an abstractmethod
"""
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from soco.exceptions import SoCoUPnPException
from spotipy.exceptions import SpotifyException

from skip_client import SkipClient, SocoSkipClient, SpotifySkipClient


# ---------------------------------------------------------------------------
# SkipClient ABC
# ---------------------------------------------------------------------------

def test_skip_client_pause_is_abstractmethod():
    """SkipClient.pause must be declared as an abstractmethod."""
    assert "pause" in SkipClient.__abstractmethods__, (
        "SkipClient.pause must be an abstractmethod"
    )


def test_skip_client_cannot_be_instantiated_without_pause():
    """Concrete subclass that omits pause() cannot be instantiated."""
    class Incomplete(SkipClient):
        async def skip(self, device_name: str, device_id: str) -> bool:
            return True
        # pause() intentionally omitted

    with pytest.raises(TypeError):
        Incomplete()


# ---------------------------------------------------------------------------
# SpotifySkipClient.pause
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_spotify_pause_calls_pause_playback_with_device_id():
    """SpotifySkipClient.pause calls sp.pause_playback(device_id) and returns True."""
    mock_sp = MagicMock()
    mock_sp.pause_playback = MagicMock(return_value=None)
    client = SpotifySkipClient(mock_sp)

    result = await client.pause("My Speaker", "device-123")

    assert result is True
    mock_sp.pause_playback.assert_called_once_with("device-123")


@pytest.mark.asyncio
async def test_spotify_pause_returns_false_on_spotify_exception(caplog):
    """SpotifySkipClient.pause returns False and logs error on SpotifyException."""
    mock_sp = MagicMock()
    mock_sp.pause_playback = MagicMock(
        side_effect=SpotifyException(http_status=403, code=-1, msg="Forbidden")
    )
    client = SpotifySkipClient(mock_sp)

    import logging
    with caplog.at_level(logging.ERROR, logger="skip_client"):
        result = await client.pause("My Speaker", "device-123")

    assert result is False
    assert any("pause" in record.message.lower() or "403" in str(record.message)
               for record in caplog.records), (
        "Expected an error log mentioning pause failure"
    )


# ---------------------------------------------------------------------------
# SocoSkipClient.pause
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soco_pause_uses_cached_ip():
    """SocoSkipClient.pause calls speaker.pause() via cached IP and returns True."""
    client = SocoSkipClient()
    client._ip_cache["Living Room"] = "192.168.1.100"

    mock_speaker = MagicMock()
    mock_speaker.pause = MagicMock(return_value=None)

    with patch("soco.SoCo", return_value=mock_speaker):
        result = await client.pause("Living Room", "device-abc")

    assert result is True
    mock_speaker.pause.assert_called_once()


@pytest.mark.asyncio
async def test_soco_pause_falls_back_to_discovery_when_not_cached():
    """SocoSkipClient.pause falls back to SSDP discovery when IP not cached, returns True."""
    client = SocoSkipClient()

    mock_speaker = MagicMock()
    mock_speaker.player_name = "Living Room"
    mock_speaker.ip_address = "192.168.1.100"
    mock_speaker.pause = MagicMock(return_value=None)

    with patch("soco.discovery.discover", return_value={mock_speaker}):
        result = await client.pause("Living Room", "device-abc")

    assert result is True
    mock_speaker.pause.assert_called_once()
    # IP should now be cached
    assert client._ip_cache.get("Living Room") == "192.168.1.100"


@pytest.mark.asyncio
async def test_soco_pause_returns_false_when_speaker_not_found(caplog):
    """SocoSkipClient.pause returns False and logs warning if speaker not found."""
    client = SocoSkipClient()

    with patch("soco.discovery.discover", return_value=set()):
        import logging
        with caplog.at_level(logging.WARNING, logger="skip_client"):
            result = await client.pause("Nonexistent Speaker", "device-abc")

    assert result is False
    assert any("not found" in record.message.lower() or "nonexistent" in record.message.lower()
               for record in caplog.records), (
        "Expected a warning log about speaker not found"
    )


# ---------------------------------------------------------------------------
# DISC-03: Updated lazy-discovery failure warning (D-08)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soco_skip_warning_includes_multicast_hint(caplog):
    """SocoSkipClient.skip() warning when speaker not found must mention multicast port and env var (D-08).

    This test is RED until Plan 04-02 updates the warning text in skip_client.py.
    """
    client = SocoSkipClient()

    with patch("soco.discovery.discover", return_value=set()):
        import logging
        with caplog.at_level(logging.WARNING, logger="skip_client"):
            result = await client.skip("Nonexistent Speaker", "device-abc")

    assert result is False
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_messages, "Expected at least one WARNING when speaker not found in skip()"
    combined = " ".join(warning_messages)
    assert "multicast UDP port 1900" in combined, (
        f"skip() WARNING must mention 'multicast UDP port 1900'. Got: {combined}"
    )
    assert "SONOS_SPEAKER_IPS" in combined, (
        f"skip() WARNING must mention 'SONOS_SPEAKER_IPS'. Got: {combined}"
    )


@pytest.mark.asyncio
async def test_soco_pause_warning_includes_multicast_hint(caplog):
    """SocoSkipClient.pause() warning when speaker not found must mention multicast port and env var (D-08).

    This test is RED until Plan 04-02 updates the warning text in skip_client.py.
    """
    client = SocoSkipClient()

    with patch("soco.discovery.discover", return_value=set()):
        import logging
        with caplog.at_level(logging.WARNING, logger="skip_client"):
            result = await client.pause("Nonexistent Speaker", "device-abc")

    assert result is False
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_messages, "Expected at least one WARNING when speaker not found in pause()"
    combined = " ".join(warning_messages)
    assert "multicast UDP port 1900" in combined, (
        f"pause() WARNING must mention 'multicast UDP port 1900'. Got: {combined}"
    )
    assert "SONOS_SPEAKER_IPS" in combined, (
        f"pause() WARNING must mention 'SONOS_SPEAKER_IPS'. Got: {combined}"
    )
