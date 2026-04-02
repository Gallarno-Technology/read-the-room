# Phase 4: Sonos Discovery Hardening - Research

**Researched:** 2026-04-02
**Domain:** SoCo SSDP discovery, asyncio executor pattern, Python logging
**Confidence:** HIGH

## Summary

Phase 4 is a focused code-quality improvement to an already-working system. The existing `SocoSkipClient` in `skip_client.py` already performs SSDP discovery lazily (on first skip). This phase promotes that discovery to an eager startup probe in `daemon.py:main()`, logs the results clearly (by speaker name + IP), updates the failure log messages to give actionable firewall hints, and reframes the `SONOS_SPEAKER_IPS` env var comment in `.env.example` from "optional but recommended" to "escape hatch."

The technical footprint is small: one new async helper function, three log message changes, and one comment edit. No new dependencies. No new env vars. No schema or API changes. The primary risk is asyncio correctness — ensuring the startup probe runs on the event loop without blocking it, consistent with the existing `run_in_executor` pattern used throughout the codebase.

**Primary recommendation:** Add `probe_sonos_speakers(soco_client)` as an async helper in `daemon.py`, call it from `main()` after `SocoSkipClient` is instantiated, before `poll_loop()` starts. Reuse `soco.discovery.discover` via `run_in_executor` exactly as the existing skip path does. Pre-seed `SocoSkipClient._ip_cache` from the probe results.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Eager SSDP discovery runs at daemon startup — before the poll loop begins. Discovered speakers are logged (name + IP) so the user can see what's on the network from container logs.
- **D-02:** If `SONOS_SPEAKER_IPS` is set, skip SSDP at startup entirely (preserve existing bypass behavior). Log that the IP override is active.
- **D-03:** The startup probe result (success or failure) is informational only — it does not block startup. The daemon starts regardless.
- **D-04:** Discovery results go to daemon logs only — no web UI changes in Phase 4.
- **D-05:** On success: log each discovered speaker as `[SONOS] Discovered: "Living Room" (192.168.1.164)` — one line per speaker, name + IP visible.
- **D-06:** On failure (no speakers found): log a single warning with a generic but actionable hint (see D-07).
- **D-07:** When SSDP finds no speakers, log: `[SONOS] No speakers found via SSDP. Ensure multicast UDP port 1900 is open on the host firewall. Set SONOS_SPEAKER_IPS=Name=IP in .env as a fallback. See README for firewall setup.`
- **D-08:** The existing lazy-discovery failure log in `SocoSkipClient.skip()` ("Spotify device name may not match Sonos room name exactly") is also updated to mention firewall/multicast as the likely cause when no speakers are found.
- **D-09:** `SONOS_SPEAKER_IPS` comment in `.env.example` changes to: "Optional escape hatch for networks where SSDP/multicast is blocked (firewalls, Proxmox LXC). SSDP is used automatically when this is unset."

### Claude's Discretion

- Where to put startup discovery logic (daemon.py `main()` or a helper function)
- Exact asyncio pattern for wrapping `soco.discovery.discover` at startup (mirrors existing `run_in_executor` pattern)
- Timeout for startup SSDP probe (use soco default — 5 seconds is fine)
- Whether startup discovery seeds the `SocoSkipClient` IP cache (good optimization, Claude's call)

### Deferred Ideas (OUT OF SCOPE)

- **Auto-activate FSM when playback switches to speaker "X"** (SONO-01/SONO-02): requires knowing which speaker is "X" — Phase 4's discovery output gives users the speaker names. The actual auto-activation logic belongs in its own phase.
- **Speaker selection UI in web dashboard**: Phase 4 is log-only, no UI changes.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISC-01 | Sonos speakers are discovered automatically via SSDP on a properly configured network — no `SONOS_SPEAKER_IPS` required | `soco.discovery.discover()` already imported in skip_client.py; startup probe in `main()` triggers it before poll loop |
| DISC-02 | `SONOS_SPEAKER_IPS` remains as an explicit override fallback, documented as an escape hatch for restricted networks | Existing `__init__` IP-seeding logic preserved; D-02 gate skips startup SSDP when env var is set; `.env.example` comment updated |
| DISC-03 | Service logs a clear, actionable message when SSDP discovery fails (includes firewall/multicast hint) | D-07 provides exact log text; D-08 updates lazy-discovery warning in `skip()` and `pause()` to add multicast hint |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| soco | 0.30.14 (pinned in requirements.txt) | SSDP multicast discovery + UPnP control | Already the project's Sonos library; `soco.discovery.discover` is the canonical API |
| asyncio | stdlib | Non-blocking event loop | Project is fully async; all blocking SoCo calls use `run_in_executor` |
| logging | stdlib | Structured log output | Project uses `logging.getLogger(__name__)` with bracketed prefix convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.2.2 (pinned) | Read `.env.example` doc update | Already loaded in daemon.py via `load_dotenv()` |

No new packages needed. This phase is zero-dependency.

**Installation:** None required.

**Version verification:** `soco==0.30.14` confirmed from `requirements.txt`. `soco.discovery.discover` signature confirmed from installed source at `.venv/lib/python3.12/site-packages/soco/discovery.py`.

## Architecture Patterns

### Existing Code Structure (relevant files only)

```
daemon.py          # main() — startup probe goes here, after SocoSkipClient() instantiation
skip_client.py     # SocoSkipClient — _ip_cache, skip(), pause() — log messages updated here
.env.example       # SONOS_SPEAKER_IPS comment — reframing only
```

### Pattern 1: Startup Probe as Async Helper Function

**What:** Extract the startup SSDP probe into a standalone `async def probe_sonos_speakers(soco_client: SocoSkipClient) -> None` in `daemon.py`. Called once from `main()` after `SocoSkipClient` is instantiated, before `poll_loop()` is invoked.

**When to use:** Claude's discretion per CONTEXT.md — a named helper keeps `main()` readable and isolates the probe logic for testing.

**Pattern:**
```python
# Source: existing skip_client.py run_in_executor pattern
async def probe_sonos_speakers(soco_client: SocoSkipClient) -> None:
    """Eager SSDP discovery at startup (D-01).

    Logs discovered speakers by name + IP (D-05). On failure, logs an
    actionable firewall hint (D-06/D-07). Skipped if SONOS_SPEAKER_IPS
    is already set (D-02). Non-blocking — daemon starts regardless (D-03).
    """
    if os.environ.get("SONOS_SPEAKER_IPS"):
        log.info("[SONOS] IP override active (SONOS_SPEAKER_IPS set) — skipping SSDP discovery")
        return

    loop = asyncio.get_event_loop()
    speakers = await loop.run_in_executor(None, soco.discovery.discover)

    if speakers:
        for speaker in speakers:
            # Pre-seed _ip_cache for first-skip latency reduction
            soco_client._ip_cache[speaker.player_name] = speaker.ip_address
            log.info('[SONOS] Discovered: "%s" (%s)', speaker.player_name, speaker.ip_address)
    else:
        log.warning(
            "[SONOS] No speakers found via SSDP. Ensure multicast UDP port 1900 is open "
            "on the host firewall. Set SONOS_SPEAKER_IPS=Name=IP in .env as a fallback. "
            "See README for firewall setup."
        )
```

**Calling site in `main()`:**
```python
soco_skip = SocoSkipClient()
spotify_skip = SpotifySkipClient(sp)

await probe_sonos_speakers(soco_skip)   # D-01: eager, non-blocking, informational

await poll_loop(sp, content_checker, soco_skip, spotify_skip)
```

### Pattern 2: Updated Lazy-Discovery Failure Log (D-08)

**What:** In `SocoSkipClient.skip()` and `SocoSkipClient.pause()`, the existing `"Spotify device name may not match Sonos room name exactly"` warning is extended to also mention firewall/multicast.

**Current text (skip_client.py line 184):**
```python
log.warning(
    "SocoSkipClient: Sonos speaker %r not found on network. "
    "Spotify device name may not match Sonos room name exactly. "
    "Caller should fall back to Spotify API skip.",
    device_name,
)
```

**Updated text:**
```python
log.warning(
    "SocoSkipClient: Sonos speaker %r not found on network. "
    "Check: (1) device name matches Sonos room name exactly, "
    "(2) multicast UDP port 1900 is open on host firewall, "
    "(3) set SONOS_SPEAKER_IPS=Name=IP in .env for restricted networks.",
    device_name,
)
```

Same change applies to the equivalent warning in `pause()` (line 249).

### Anti-Patterns to Avoid

- **Blocking the event loop:** Never call `soco.discovery.discover` directly in an async function without `run_in_executor`. It blocks for up to 5 seconds (SSDP timeout). The existing skip path wraps it correctly — the startup probe must do the same.
- **Making startup blocking on discovery success:** D-03 is explicit — the probe is informational. Do not raise or exit on empty results. Do not `await` the probe inside a try/except that swallows the startup signal.
- **Checking `_ip_cache` directly in tests via private access:** Acceptable here — `_ip_cache` is already tested this way in `test_skip_client.py`. Keep consistent.
- **Separate SSDP call in daemon.py:** Do not re-import `soco.discovery` in `daemon.py` — delegate discovery to the `SocoSkipClient` instance (or pass `soco_client` to the probe helper so it can seed the cache). This keeps SoCo logic in `skip_client.py` and its tests.

  > Clarification: The probe helper in `daemon.py` may directly call `soco.discovery.discover` because `daemon.py` already imports from `skip_client` and this is a startup-only path, not a hot path. Alternatively, the probe can be a method on `SocoSkipClient` itself. Both are valid — see Open Questions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multicast SSDP discovery | Custom UDP socket code | `soco.discovery.discover(timeout=5)` | SoCo handles socket creation, TTL=4, multicast group join, response parsing — all UPnP-correct. The source in discovery.py is ~200 lines handling edge cases. |
| Speaker name normalization | Custom fuzzy matching | `.strip().lower()` equality (already in skip_client.py) | Already proven in UAT Test 5 per existing code comments — no need to change. |
| Asyncio thread-pool dispatch | `asyncio.run_in_executor` reimplementation | `loop.run_in_executor(None, soco.discovery.discover)` | Existing pattern throughout the codebase. `None` uses the default ThreadPoolExecutor. |

**Key insight:** This phase requires zero new algorithms. Every pattern already exists in the codebase — the startup probe is a copy-and-adapt of the existing lazy-discovery path.

## Common Pitfalls

### Pitfall 1: `soco.discovery.discover` returns `None`, not empty set, on failure

**What goes wrong:** Code checks `if not speakers` which catches both `None` and empty set correctly — but code that checks `if speakers is None` misses the case where `discover` returns an empty set `set()`.

**Why it happens:** The docstring says "return `None` if no zones found" — but in some SoCo versions/paths it may return an empty set. The current `skip_client.py` already handles this correctly with `if all_speakers:`.

**How to avoid:** Use `if speakers:` (falsy check) not `if speakers is None:`. Match the existing `skip_client.py` pattern exactly.

**Warning signs:** SSDP succeeds but returns zero results — probe logs "No speakers found" even when speakers are present.

### Pitfall 2: Event loop reference at startup

**What goes wrong:** Using `asyncio.get_event_loop()` in `main()` context works correctly because `main()` is itself a coroutine run by `asyncio.run()`. The probe helper will also be `await`ed from `main()`, so the same running loop is in scope.

**Why it happens:** `asyncio.get_event_loop()` vs `asyncio.get_running_loop()` — the existing codebase uses `asyncio.get_event_loop()` consistently. Switching to `asyncio.get_running_loop()` inside a coroutine is safe and more explicit, but not required for correctness here.

**How to avoid:** Follow the existing pattern (`asyncio.get_event_loop()`) for consistency. Do not use `asyncio.new_event_loop()`.

### Pitfall 3: Cache pre-seeding creates name-collision with env var entries

**What goes wrong:** If `SONOS_SPEAKER_IPS` is NOT set but SSDP finds a speaker whose name was previously in the cache (from a prior restart where env var WAS set), the cache entry gets overwritten with a potentially stale IP.

**Why it happens:** `_ip_cache` is populated at `__init__` from env var, and the probe runs immediately after instantiation. If the env var is set, D-02 skips SSDP, so no collision. If the env var is NOT set, the cache starts empty, so SSDP results always go in cleanly. No collision possible.

**How to avoid:** The D-02 gate (`if os.environ.get("SONOS_SPEAKER_IPS"): return`) prevents any overlap. No extra guard needed.

### Pitfall 4: 5-second startup blocking perception

**What goes wrong:** `soco.discovery.discover` defaults to `timeout=5`. Users see a 5-second gap in logs before "Daemon started" message.

**Why it happens:** SSDP blocks for the full timeout waiting for responses. Even when speakers respond quickly, the socket waits for the timeout to expire before returning.

**How to avoid:** The probe runs before `poll_loop` — log a `[SONOS] Starting SSDP discovery...` message before the call so the 5-second delay has a visible explanation. Per D-03, the probe does NOT block the daemon from starting — the poll loop starts immediately after the probe resolves (whether it found speakers or not). The 5-second delay is at startup only, not per-poll.

**Note:** The default timeout of 5 seconds is acceptable per CONTEXT.md ("use soco default — 5 seconds is fine"). No timeout customization needed.

## Code Examples

### Full probe_sonos_speakers helper
```python
# Source: soco.discovery.discover — .venv/lib/python3.12/site-packages/soco/discovery.py
# Pattern: existing run_in_executor usage in skip_client.py (lines 171-173, 237-239)
import asyncio
import logging
import os
import soco.discovery

log = logging.getLogger(__name__)

async def probe_sonos_speakers(soco_client) -> None:
    """Eager SSDP probe at daemon startup (D-01, D-02, D-03, D-05, D-06, D-07).

    Skipped if SONOS_SPEAKER_IPS is set (D-02). Non-blocking — probe result
    is informational only (D-03). Pre-seeds _ip_cache as optimization.
    """
    if os.environ.get("SONOS_SPEAKER_IPS"):
        log.info("[SONOS] IP override active (SONOS_SPEAKER_IPS set) — skipping SSDP discovery")
        return

    log.info("[SONOS] Starting SSDP discovery (timeout=5s)...")
    loop = asyncio.get_event_loop()
    speakers = await loop.run_in_executor(None, soco.discovery.discover)

    if speakers:
        for speaker in speakers:
            soco_client._ip_cache[speaker.player_name] = speaker.ip_address
            log.info('[SONOS] Discovered: "%s" (%s)', speaker.player_name, speaker.ip_address)
    else:
        log.warning(
            "[SONOS] No speakers found via SSDP. Ensure multicast UDP port 1900 is open "
            "on the host firewall. Set SONOS_SPEAKER_IPS=Name=IP in .env as a fallback. "
            "See README for firewall setup."
        )
```

### Updated lazy-discovery failure warning (skip_client.py — both skip() and pause())
```python
# Source: existing pattern, extending lines 183-188 and 249-253
# Applies to BOTH skip() and pause() — same warning text, different method context
if device is None:
    log.warning(
        "SocoSkipClient: Sonos speaker %r not found on network. "
        "Check: (1) device name matches Sonos room name exactly, "
        "(2) multicast UDP port 1900 is open on host firewall, "
        "(3) set SONOS_SPEAKER_IPS=Name=IP in .env for restricted networks.",
        device_name,
    )
    return False
```

### .env.example SONOS_SPEAKER_IPS comment update
```bash
# Sonos speaker IP addresses — optional escape hatch for networks where SSDP/multicast is
# blocked (firewalls, Proxmox LXC without bridge multicast forwarding). SSDP is used
# automatically when this is unset. Format: "Room Name=IP,Other Room=IP"
# (use the exact name Spotify reports for the device)
# Find IPs in the Sonos app: Settings -> System -> [Room] -> About [Room]
# SONOS_SPEAKER_IPS=Dining Room=192.168.1.50,Living Room=192.168.1.51
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SONOS_SPEAKER_IPS` framed as "optional but recommended" | `SONOS_SPEAKER_IPS` framed as escape hatch; SSDP is first-class | Phase 4 | Changes user mental model: SSDP works by default, IP var is for broken networks |
| Lazy SSDP discovery (only on skip) | Eager SSDP probe at startup + lazy fallback remains | Phase 4 | Startup logs show speaker roster; first-skip has no SSDP delay (cache pre-seeded) |

## Open Questions

1. **Should `probe_sonos_speakers` be a standalone function in `daemon.py` or a method on `SocoSkipClient`?**
   - What we know: CONTEXT.md says "Where to put startup discovery logic (daemon.py `main()` or a helper function)" is Claude's discretion.
   - What's unclear: A method on `SocoSkipClient` would keep all SoCo logic in one file and make it easier to unit-test without importing daemon.py. A standalone function in `daemon.py` matches the module's existing responsibility.
   - Recommendation: Standalone async function in `daemon.py` — the probe is a startup orchestration concern, not a skip-client concern. The cache pre-seeding passes `soco_client` as a parameter, keeping the dependency explicit.

2. **Should the `[SONOS] Starting SSDP discovery...` pre-probe log line be included?**
   - What we know: D-05 specifies the success format; D-07 specifies the failure format. No spec for a "starting" log.
   - What's unclear: Without it, a 5-second gap in logs at startup has no explanation.
   - Recommendation: Include a brief info log before the `run_in_executor` call so the delay is explained in logs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| soco | SSDP discovery | Already installed | 0.30.14 (confirmed in requirements.txt and .venv) | — |
| Python 3.12 | Runtime | Already in .venv | 3.12 | — |
| pytest + pytest-asyncio | Test validation | Checked below | see Validation | — |

Step 2.6: No new external dependencies. All tools available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing tests/test_skip_client.py uses both) |
| Config file | None — conftest.py adds sys.path; pytest-asyncio configured via decorator |
| Quick run command | `python -m pytest tests/test_skip_client.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DISC-01 | `probe_sonos_speakers` calls `soco.discovery.discover` when SONOS_SPEAKER_IPS is not set, logs discovered speakers | unit | `python -m pytest tests/test_sonos_probe.py -x -q` | Wave 0 |
| DISC-02 | `probe_sonos_speakers` skips SSDP and logs IP override when SONOS_SPEAKER_IPS is set; `_ip_cache` is pre-seeded from env var on success path | unit | `python -m pytest tests/test_sonos_probe.py -x -q` | Wave 0 |
| DISC-03 | `probe_sonos_speakers` logs the exact D-07 warning when no speakers found; `SocoSkipClient.skip()` and `.pause()` updated warning includes multicast hint | unit | `python -m pytest tests/test_sonos_probe.py tests/test_skip_client.py -x -q` | Wave 0 (new tests in test_sonos_probe.py); test_skip_client.py exists but needs new test for updated warning |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_sonos_probe.py` — covers DISC-01, DISC-02, DISC-03 probe behavior
- [ ] New test in `tests/test_skip_client.py` — verifies updated warning text in `skip()` and `pause()` includes multicast hint (DISC-03)

Note: `tests/conftest.py` exists and adds sys.path. pytest and pytest-asyncio are used by existing tests — verify they are installed in the venv before Wave 0.

## Sources

### Primary (HIGH confidence)
- `.venv/lib/python3.12/site-packages/soco/discovery.py` — `discover()` signature: `timeout=5`, returns `set[SoCo] | None`; confirmed SSDP uses UDP multicast, blocks for `timeout` seconds
- `skip_client.py` (project source) — existing `run_in_executor` pattern, `_ip_cache` structure, log message text
- `daemon.py` (project source) — `main()` structure, `SocoSkipClient()` instantiation site, `asyncio.get_event_loop()` pattern
- `.env.example` (project source) — current `SONOS_SPEAKER_IPS` comment text
- `tests/test_skip_client.py` (project source) — existing test patterns (mock `soco.discovery.discover`, assert `_ip_cache`)
- `04-CONTEXT.md` — locked decisions D-01 through D-09

### Secondary (MEDIUM confidence)
- `requirements.txt` — confirms soco==0.30.14, no new packages needed

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; no new dependencies
- Architecture: HIGH — startup probe pattern is a direct adaptation of existing lazy-discovery code; soco API confirmed from installed source
- Pitfalls: HIGH — identified from reading actual source code (discover returns `None` not empty set) and from existing code comments (UAT Test 5 note, run_in_executor pattern)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (soco 0.30.14 is pinned; no external dependency changes expected)
