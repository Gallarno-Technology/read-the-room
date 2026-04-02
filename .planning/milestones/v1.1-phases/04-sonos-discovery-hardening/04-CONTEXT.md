# Phase 4: Sonos Discovery Hardening - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Make SSDP auto-discovery first-class: the daemon discovers Sonos speakers automatically at startup on properly configured networks (multicast UDP port 1900 open). `SONOS_SPEAKER_IPS` becomes an explicitly-documented escape hatch for restricted networks (firewalled, Proxmox LXC without bridge multicast, etc.). When discovery fails, the log must give a concrete, actionable hint. No web UI changes. No speaker-selection UI.

</domain>

<decisions>
## Implementation Decisions

### Discovery Timing
- **D-01:** Eager SSDP discovery runs at daemon startup — before the poll loop begins. Discovered speakers are logged (name + IP) so the user can see what's on the network from container logs.
- **D-02:** If `SONOS_SPEAKER_IPS` is set, skip SSDP at startup entirely (preserve existing bypass behavior). Log that the IP override is active.
- **D-03:** The startup probe result (success or failure) is informational only — it does not block startup. The daemon starts regardless.

### Discovery Output
- **D-04:** Discovery results go to daemon logs only — no web UI changes in Phase 4.
- **D-05:** On success: log each discovered speaker as `[SONOS] Discovered: "Living Room" (192.168.1.164)` — one line per speaker, name + IP visible.
- **D-06:** On failure (no speakers found): log a single warning with a generic but actionable hint (see D-07).

### Failure Message
- **D-07:** When SSDP finds no speakers, log: `[SONOS] No speakers found via SSDP. Ensure multicast UDP port 1900 is open on the host firewall. Set SONOS_SPEAKER_IPS=Name=IP in .env as a fallback. See README for firewall setup.` — generic hint referencing port 1900, the env var escape hatch, and the README.
- **D-08:** The existing lazy-discovery failure log in `SocoSkipClient.skip()` ("Spotify device name may not match Sonos room name exactly") is also updated to mention firewall/multicast as the likely cause when no speakers are found.

### `.env.example` Framing
- **D-09:** `SONOS_SPEAKER_IPS` comment in `.env.example` changes from "optional but recommended — bypasses unreliable SSDP discovery" to something like: "Optional escape hatch for networks where SSDP/multicast is blocked (firewalls, Proxmox LXC). SSDP is used automatically when this is unset."

### Claude's Discretion
- Where to put startup discovery logic (daemon.py `main()` or a helper function)
- Exact asyncio pattern for wrapping `soco.discovery.discover` at startup (mirrors existing `run_in_executor` pattern)
- Timeout for startup SSDP probe (use soco default — 5 seconds is fine)
- Whether startup discovery seeds the `SocoSkipClient` IP cache (good optimization, Claude's call)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing implementation
- `skip_client.py` — `SocoSkipClient.__init__()` (IP cache seeding from `SONOS_SPEAKER_IPS`), `skip()` and `pause()` methods (existing lazy SSDP + cache pattern). Startup probe must be consistent with this.
- `daemon.py` — `main()` function (where startup probe goes), `poll_loop()` (existing skip path that triggers lazy discovery)

### Configuration
- `.env.example` — `SONOS_SPEAKER_IPS` comment needs reframing (D-09)
- `docker-compose.yml` — `network_mode: host` already set (required for SSDP multicast — do not change)

### Requirements
- `.planning/REQUIREMENTS.md` — DISC-01, DISC-02, DISC-03 (the three requirements this phase covers)

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `soco.discovery.discover` — already imported and used in `SocoSkipClient`. Startup probe reuses the same call wrapped in `run_in_executor`.
- `SocoSkipClient._ip_cache` — startup discovery can pre-seed this cache, eliminating per-skip discovery latency for the first skip.
- `SocoSkipClient.__init__()` IP seeding loop — startup probe can follow the same pattern to pre-populate the cache from SSDP results.

### Established Patterns
- All SoCo calls wrapped in `asyncio.get_event_loop().run_in_executor(None, ...)` — startup probe follows this pattern.
- Structured log lines with bracketed prefix (`[SKIP]`, `[SONOS]`) — new log lines use `[SONOS]` prefix.
- All config from `.env` — no new env vars needed beyond clarifying `SONOS_SPEAKER_IPS` framing.

### Integration Points
- `daemon.py:main()` — startup SSDP probe runs here, after `SocoSkipClient` is instantiated, before `poll_loop()` is called.
- `SocoSkipClient._ip_cache` — startup probe results can pre-seed this so first-skip has no SSDP delay.
- Startup probe skips if `SONOS_SPEAKER_IPS` is already set (IP cache already pre-seeded in `__init__()`).

</code_context>

<specifics>
## Specific Ideas

- User wants Phase 4 discovery to set up the ground for a future phase where FSM auto-activates when playback switches to a specific Sonos speaker (SONO-01/SONO-02 in REQUIREMENTS.md v2). The startup probe's speaker listing (name + IP) gives users the info they need to configure that future feature.
- "During setup we should run discovery and show the user what speakers are found" — captured as D-01/D-05: startup probe logs discovered speakers by name + IP.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-activate FSM when playback switches to speaker "X"** (SONO-01/SONO-02): User wants this eventually. Requires knowing which speaker is "X" — Phase 4's discovery output (D-05) gives users the speaker names they'd need to configure this. The actual auto-activation logic belongs in its own phase.
- **Speaker selection UI in web dashboard**: Showing discovered speakers in the dashboard would help with the future auto-FSM feature. Deferred — Phase 4 is log-only, no UI changes.

</deferred>

---

*Phase: 04-sonos-discovery-hardening*
*Context gathered: 2026-04-02*
