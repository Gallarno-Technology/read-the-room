---
status: investigating
trigger: "Diagnose why the Sonos speaker is not being detected — daemon logs `[DEVICE] name='unknown' is_restricted=False` when playing on Sonos, then uses SpotifySkipClient instead of SocoSkipClient and gets a 403 Restricted device"
created: 2026-04-01T00:00:00
updated: 2026-04-01T00:00:00
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: The routing condition on daemon.py:151 is INVERTED — it selects soco_skip when is_restricted=True and spotify_skip when is_restricted=False, but Sonos devices report is_restricted=True from Spotify. The observed log shows is_restricted=False which is contradicted by the 403 from Spotify. Additionally, the device name is 'unknown' which means the device field was missing entirely from the API response, causing all .get() defaults to trigger.
test: Code audit of daemon.py lines 134-151 and cross-reference with Spotify API docs on the `device` field placement in /me/player/currently-playing vs /me/player.
expecting: The `device` key is absent from /me/player/currently-playing responses, causing device={} default and is_restricted=False default. The routing logic then sends all skips to SpotifySkipClient (the wrong path for Sonos).
next_action: CONFIRMED — both issues found in static analysis. Document resolution.

## Symptoms

expected: Daemon detects Sonos speaker, routes skip through SocoSkipClient via SoCo/UPnP
actual: Daemon logs name='unknown' is_restricted=False, routes to SpotifySkipClient, gets 403 Restricted device
errors: "HTTP Error for POST to https://api.spotify.com/v1/me/player/next ... returned 403 due to Restricted device"
reproduction: Play music on Sonos speaker while family_safe_mode=True and an explicit track starts
started: Presumably always broken — design-level bug

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-04-01T00:00:00
  checked: daemon.py line 134 — how device is extracted from Spotify API response
  found: `device = result.get("device", {})` where `result` is the response from `sp.currently_playing()` which calls GET /me/player/currently-playing
  implication: The Spotify /me/player/currently-playing endpoint does NOT include a `device` field in its response body. The `device` object is only present on GET /me/player (the full playback state endpoint). So `result.get("device", {})` always returns `{}`.

- timestamp: 2026-04-01T00:00:00
  checked: daemon.py lines 135-136 — how device_name and is_restricted are extracted
  found: `device_name = device.get("name", "unknown")` and `is_restricted = device.get("is_restricted", False)` — both fall back to their defaults because device is always `{}`
  implication: device_name is always "unknown", is_restricted is always False. This explains the log line exactly.

- timestamp: 2026-04-01T00:00:00
  checked: daemon.py line 151 — the routing decision
  found: `client = soco_skip if is_restricted else spotify_skip`
  implication: Because is_restricted is always False (from the empty device dict), spotify_skip is always selected regardless of whether the device is Sonos.

- timestamp: 2026-04-01T00:00:00
  checked: skip_client.py docstring and class comment
  found: SocoSkipClient docstring says "Sonos speakers (is_restricted=True devices)" — confirming the design intent is that Sonos == is_restricted=True. But the data never arrives to make that true.
  implication: The routing logic direction itself is correct (soco when restricted), but the data it relies on is never populated because the wrong Spotify endpoint is used.

## Resolution

root_cause: `sp.currently_playing()` calls GET /me/player/currently-playing, which does not return a `device` object in its response. The `device` key is only present in GET /me/player (full playback state). As a result, `result.get("device", {})` always returns an empty dict, `is_restricted` defaults to False, and the skip client routing always selects SpotifySkipClient — even for Sonos speakers that Spotify itself marks as restricted.

fix: Replace the `sp.currently_playing()` call with `sp.current_playback()` (which calls GET /me/player and includes the full `device` object with `is_restricted`, `name`, `id`, etc.). Alternatively, keep `currently_playing()` for track data but make a separate `sp.current_playback()` call to get device info on track change events.

files_changed: []
