#!/usr/bin/env python3
"""Skip client abstractions for Spotify Family Safe Mode (Phase 2).

Provides a SkipClient ABC and two concrete implementations:
- SpotifySkipClient: skips via Spotify Web API (non-Sonos devices)
- SocoSkipClient: skips via SoCo UPnP (Sonos speakers, is_restricted=True)

Design (D-03, D-04): The ABC allows a future BridgeSkipClient to be added
without modifying daemon.py — just instantiate the new implementation there.
"""
import asyncio
import logging
from abc import ABC, abstractmethod

import soco
import soco.discovery
import spotipy
from soco.exceptions import SoCoUPnPException
from spotipy.exceptions import SpotifyException

log = logging.getLogger(__name__)


class SkipClient(ABC):
    """Abstract skip client. Implementations must be safe to call from async code."""

    @abstractmethod
    async def skip(self, device_name: str, device_id: str) -> bool:
        """Skip the current track.

        Args:
            device_name: Human-readable device name from Spotify API.
            device_id: Spotify device ID (used by SpotifySkipClient).

        Returns:
            True on success, False on failure.
        """
        ...

    @abstractmethod
    async def pause(self, device_name: str, device_id: str) -> bool:
        """Pause the current playback.

        Args:
            device_name: Human-readable device name from Spotify API.
            device_id: Spotify device ID (used by SpotifySkipClient).

        Returns:
            True on success, False on failure.
        """
        ...


class SpotifySkipClient(SkipClient):
    """Skip via Spotify Web API POST /me/player/next.

    Requires scope: user-modify-playback-state (SKIP-02).
    """

    def __init__(self, sp: spotipy.Spotify) -> None:
        self.sp = sp

    async def skip(self, device_name: str, device_id: str) -> bool:
        """Skip to next track using Spotify API.

        Wraps synchronous spotipy call in run_in_executor to avoid blocking
        the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.sp.next_track, device_id)
            log.debug("SpotifySkipClient: skipped on device %r (%s)", device_name, device_id)
            return True
        except SpotifyException as exc:
            log.error(
                "SpotifySkipClient: skip failed for device %r: %s", device_name, exc
            )
            return False

    async def pause(self, device_name: str, device_id: str) -> bool:
        """Pause playback using Spotify API.

        Passes device_id so the API targets the correct device — bare
        sp.pause_playback() with no device_id silently fails for non-active
        sessions.

        Wraps synchronous spotipy call in run_in_executor to avoid blocking
        the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.sp.pause_playback, device_id)
            log.debug("SpotifySkipClient: paused device %r (%s)", device_name, device_id)
            return True
        except SpotifyException as exc:
            log.error(
                "SpotifySkipClient: pause failed for device %r: %s", device_name, exc
            )
            return False


class SocoSkipClient(SkipClient):
    """Skip via SoCo UPnP for Sonos speakers (is_restricted=True devices).

    Caches speaker IP after first successful discovery to avoid slow SSDP
    multicast on subsequent skips (Pitfall 6 from RESEARCH.md).
    """

    def __init__(self) -> None:
        # IP cache: device_name -> ip_address
        self._ip_cache: dict[str, str] = {}

    async def skip(self, device_name: str, device_id: str) -> bool:
        """Skip to next track on a Sonos speaker.

        Attempts cached IP first, falls back to SoCo discovery by name.
        Wraps synchronous SoCo calls in run_in_executor to avoid blocking
        the asyncio event loop.
        """
        loop = asyncio.get_event_loop()

        # Try cached IP first — bypasses slow SSDP multicast discovery
        if device_name in self._ip_cache:
            cached_ip = self._ip_cache[device_name]
            try:
                speaker = soco.SoCo(cached_ip)
                await loop.run_in_executor(None, speaker.next)
                log.debug(
                    "SocoSkipClient: skipped via cached IP %s for %r",
                    cached_ip, device_name,
                )
                return True
            except SoCoUPnPException as exc:
                log.warning(
                    "SocoSkipClient: cached IP %s failed for %r, retrying discovery: %s",
                    cached_ip, device_name, exc,
                )
                # Cache miss — fall through to discovery
                del self._ip_cache[device_name]

        # SSDP multicast — discover all speakers, match by normalized name
        # soco.discovery.by_name does strict case-sensitive equality; discover()
        # + .strip().lower() tolerates casing/whitespace differences (UAT Test 5).
        all_speakers = await loop.run_in_executor(
            None, soco.discovery.discover
        )
        device = None
        if all_speakers:
            target = device_name.strip().lower()
            for speaker in all_speakers:
                if speaker.player_name.strip().lower() == target:
                    device = speaker
                    break

        if device is None:
            log.warning(
                "SocoSkipClient: Sonos speaker %r not found on network. "
                "Spotify device name may not match Sonos room name exactly. "
                "Caller should fall back to Spotify API skip.",
                device_name,
            )
            return False

        # Cache IP for future skips
        self._ip_cache[device_name] = device.ip_address

        try:
            await loop.run_in_executor(None, device.next)
            log.debug(
                "SocoSkipClient: skipped via discovery for %r (IP cached: %s)",
                device_name, device.ip_address,
            )
            return True
        except SoCoUPnPException as exc:
            log.error(
                "SocoSkipClient: UPnP error skipping on %r: %s", device_name, exc
            )
            return False

    async def pause(self, device_name: str, device_id: str) -> bool:
        """Pause playback on a Sonos speaker.

        Mirrors the exact structure of skip(): attempts cached IP first, then
        falls back to SSDP discovery. Uses speaker.pause() instead of
        speaker.next(). Wraps synchronous SoCo calls in run_in_executor to
        avoid blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()

        # Try cached IP first — bypasses slow SSDP multicast discovery
        if device_name in self._ip_cache:
            cached_ip = self._ip_cache[device_name]
            try:
                speaker = soco.SoCo(cached_ip)
                await loop.run_in_executor(None, speaker.pause)
                log.debug(
                    "SocoSkipClient: paused via cached IP %s for %r",
                    cached_ip, device_name,
                )
                return True
            except SoCoUPnPException as exc:
                log.warning(
                    "SocoSkipClient: cached IP %s failed for %r during pause, retrying discovery: %s",
                    cached_ip, device_name, exc,
                )
                # Cache miss — fall through to discovery
                del self._ip_cache[device_name]

        # SSDP multicast — discover all speakers, match by normalized name
        all_speakers = await loop.run_in_executor(
            None, soco.discovery.discover
        )
        device = None
        if all_speakers:
            target = device_name.strip().lower()
            for speaker in all_speakers:
                if speaker.player_name.strip().lower() == target:
                    device = speaker
                    break

        if device is None:
            log.warning(
                "SocoSkipClient: Sonos speaker %r not found on network during pause. "
                "Spotify device name may not match Sonos room name exactly.",
                device_name,
            )
            return False

        # Cache IP for future operations
        self._ip_cache[device_name] = device.ip_address

        try:
            await loop.run_in_executor(None, device.pause)
            log.debug(
                "SocoSkipClient: paused via discovery for %r (IP cached: %s)",
                device_name, device.ip_address,
            )
            return True
        except SoCoUPnPException as exc:
            log.error(
                "SocoSkipClient: UPnP error pausing on %r: %s", device_name, exc
            )
            return False
