# Phase 2: Content Filtering & Auto-Skip - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

When Family Safe Mode is on, tracks that violate family-safe rules are automatically skipped — via SoCo for Sonos speakers, Spotify API for all other devices — before children hear more than a second or two. Three-tier filter: explicit Spotify flag → LRCLIB lyrics fetch → profanity scan. Includes FSM toggle and lyrics cache. Signal/Web UI notifications are NOT part of this phase — Phase 2 logs skip events to stdout only.

</domain>

<decisions>
## Implementation Decisions

### Sonos Device Detection
- **D-01:** Detect Sonos speakers using the Spotify `is_restricted: true` device flag from the currently-playing API response. No SoCo network scan at startup, no user-configured room name list.
- **D-02:** Log the device name and `is_restricted` value on every track change so detection can be debugged easily.

### Skip Path Architecture
- **D-03:** Abstract the skip action behind a `SkipClient` interface with two concrete implementations: `SocoSkipClient` (local UPnP, self-hosted) and `SpotifySkipClient` (Spotify API, non-Sonos). The daemon selects at runtime based on D-01.
- **D-04:** The interface must be designed so a future `BridgeSkipClient` (central-hosting path via local LAN bridge) can be plugged in without modifying daemon.py. Self-host remains the primary deployment target for v1.

### Family Safe Mode Toggle (Phase 2)
- **D-05:** FSM is toggled via `make fsm-on` and `make fsm-off` Makefile targets. These write `{"family_safe_mode": true/false}` into state.json. Phase 3 (Web UI) will add in-browser toggle.
- **D-06:** Daemon reads `family_safe_mode` from state.json on every poll cycle (not cached at startup), so toggle takes effect within one poll interval (~1s).

### Phase 2 Notifications (Log Only)
- **D-07:** Phase 2 has no notification delivery (Signal dropped; Web UI arrives in Phase 3). All skip events, profanity detections, and FSM state changes are written as structured log lines to stdout. Log format: `[SKIP] reason=explicit track="X" artist="Y"` — machine-parseable for future ingestion by the Web UI.

### Profanity Scanning
- **D-08:** Default threshold: moderate/severe words only (not any-match). The `obscenity` library exposes severity tiers — mild language ("damn", "hell") passes through at default settings.
- **D-09:** Log the **severity score** for every scanned track to stdout, including tracks that are NOT skipped. Format: `[SCAN] track="X" artist="Y" severity=2 matched=["word"] action=allow`. This enables threshold tuning without re-scanning.
- **D-10:** Threshold is configurable via env var `PROFANITY_MIN_SEVERITY` (integer, default 2 = moderate). Phase 2 reads this from `.env`. Multi-family per-user config is a future concern.

### Multi-Family / Central Hosting Direction
- **D-11:** Self-host (single Proxmox/Docker deployment) remains the primary and only supported mode for v1. However, all skip paths and config must use the abstracted interfaces from D-03/D-04 so central hosting can be layered on without rewriting the daemon.
- **D-12:** No per-user data model, auth layer, or multi-tenancy in Phase 2. These are prerequisites for central hosting and belong to a future milestone.

### Claude's Discretion
- SQLite schema for lyrics cache (FILT-06) — column names, indexes, cache TTL strategy
- Exact SoCo method calls for skip (`next_track()` vs transport skip)
- Error handling for LRCLIB rate limits and timeouts
- How consecutive-skip count is tracked across the poll loop (in-memory vs state.json)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — FILT-01 through FILT-06, SKIP-01 through SKIP-03, FSM-01, FSM-02 (all Phase 2 requirements)

### Existing Phase 1 Code
- `daemon.py` — poll loop attach point; `poll_loop()` is where ContentChecker integrates; `state.json` schema must be extended (not replaced)
- `state.json` — must add `family_safe_mode` key (Phase 1 schema: `{"last_track_id": null}`)
- `docker-compose.yml` — `network_mode: host` already set (required for SoCo UPnP)
- `.env.example` — new env vars (`PROFANITY_MIN_SEVERITY`, `SONOS_CACHE_PATH`, `LYRICS_DB_PATH`) must be added here

### Project Context
- `.planning/PROJECT.md` — core value statement, out-of-scope list, evolution rules

No external specs — requirements are fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `daemon.py:load_state()` / `save_state()` — extend to read/write `family_safe_mode` key; existing direct-write pattern (no atomic rename) should be preserved
- `docker-compose.yml` bind mount pattern — SQLite DB file and lyrics cache should follow same bind-mount pattern as `state.json`
- `Makefile` — `make fsm-on` / `make fsm-off` targets follow existing `make up` / `make down` pattern

### Established Patterns
- All config from `.env` via `python-dotenv` — new env vars follow this pattern
- Structured log lines to stdout — extend with `[SKIP]`, `[SCAN]`, `[FSM]` prefixes for machine parseability
- Direct file write (not atomic rename) — required for bind-mounted files on Linux (EBUSY constraint from Phase 1)

### Integration Points
- `poll_loop()` in `daemon.py` (~line 72): after track-change detection, invoke `ContentChecker.check(track)` → returns `(action: allow|skip, reason: str, severity: int)`
- `state.json`: add `family_safe_mode: bool` key; daemon reads it each poll cycle
- New modules: `content_checker.py`, `lyrics_service.py`, `skip_client.py` (with `SocoSkipClient`, `SpotifySkipClient` impls)

</code_context>

<specifics>
## Specific Ideas

- "I would like to know what severity scores songs are getting" — log severity for ALL scanned tracks, not just skips (D-09)
- "Configuration would be a must" for multi-family — `PROFANITY_MIN_SEVERITY` env var in Phase 2, per-family config deferred to central hosting milestone
- Web UI should eventually be able to ingest the structured log lines — keep format consistent and machine-parseable (D-07)

</specifics>

<deferred>
## Deferred Ideas

- **Web UI (Phase 3 replacement)**: Signal is dropped. Phase 3 should become a Web UI — dashboard showing skip history, FSM toggle, ambiguous track allow/skip prompts, notification feed. Roadmap needs updating before Phase 3 planning.
- **Sonos Cloud API**: Remote Sonos control without a local bridge — viable for central-hosting path but requires OAuth per household. Backlog for post-v1.
- **Local bridge for central hosting**: A lightweight LAN agent that receives skip commands from a central service and executes SoCo locally. Architecture is pre-wired via D-03/D-04 — build when central hosting milestone begins.
- **Per-family profanity threshold**: Central hosting will need per-user `PROFANITY_MIN_SEVERITY` stored in a user config store, not a flat env var.
- **Non-English profanity detection**: Out of scope per REQUIREMENTS.md — defer to v2.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 2 scope.

</deferred>

---

*Phase: 02-content-filtering-auto-skip*
*Context gathered: 2026-04-01*
