# Spotify Family Safe Mode

## What This Is

A background service running on a home server that monitors Spotify playback and automatically skips songs that violate family-safe content rules when Family Safe Mode is active. It uses Spotify's explicit flag and lyric scanning (via LRCLIB) to filter content, with a real-time web dashboard for monitoring and control. Integrates with Sonos speakers via SoCo UPnP and Spotify Web API. The dashboard now supports four named filter profiles — parents select a profile that controls which content rules apply. Built for a parent who wants to listen freely but not expose young children (ages 3 and 7) to explicit lyrics or heavy curse words.

## Core Value

Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## Requirements

### Validated

- ✓ Service monitors currently playing Spotify track in real-time — v1.0
- ✓ User can toggle Family Safe Mode on/off — v1.0
- ✓ Songs marked explicit by Spotify are auto-skipped — v1.0
- ✓ Songs with curse words detected in lyrics are auto-skipped — v1.0
- ✓ Skip works on Sonos speakers (SoCo UPnP) — v1.0
- ✓ Skip works on non-Sonos devices (Spotify Web API) — v1.0
- ✓ Service runs as a Docker container with restart:always — v1.0
- ✓ After 5 consecutive explicit skips, playback pauses — v1.0
- ✓ Real-time skip history feed in browser dashboard — v1.0
- ✓ FSM toggle accessible from browser dashboard — v1.0
- ✓ Sonos SSDP discovery works without manual IP configuration — v1.1
- ✓ Project has a complete clone-and-run README usable by anyone with Docker — v1.1
- ✓ Service survives host reboots without manual intervention — v1.1
- ✓ Silently hung daemon container restarted automatically by Docker healthcheck — v1.1
- ✓ web_ui exposes GET /now-playing (hydration) and POST /skip (manual skip via Spotify API) — v1.2
- ✓ Dashboard shows current track with real-time filter evaluation state badge — v1.2
- ✓ Parent can manually skip current track from dashboard without opening Spotify — v1.2
- ✓ Dashboard badge shows "Mild language" alongside "Passed" when severity=1 — v1.2
- ✓ ContentChecker.check() returns named TrackEvalResult dataclass instead of positional 3-tuple — v1.3
- ✓ Drug reference detection in lyrics — boolean signal — v1.3
- ✓ Sexual content detection in lyrics — boolean signal — v1.3
- ✓ Both new signals logged in incident log alongside existing flags — v1.3
- ✓ Dashboard shows drug reference and sexual content badge variants in skip feed — v1.3
- ✓ When lyrics unavailable, scan track title + artist before allowing — v1.3
- ✓ Dashboard accurately shows idle state when nothing is playing — v1.4 (IDLE-01, IDLE-02)
- ✓ Skip feed history persists across page refresh and SSE reconnect — v1.4 (HIST-01, HIST-02, HIST-03)
- ✓ Parent can select a named filter profile from dashboard UI — v1.4 (PROF-01, PROF-04)
- ✓ Active profile persists in state.json and survives service restart — v1.4 (PROF-02)
- ✓ ContentChecker applies the active profile's per-scanner rules — v1.4 (PROF-03)

### Active

- [ ] Rebrand app display name to "Read the Room" across UI, README, and project docs
- [ ] Info icon on each filter profile showing what content it skips
- [ ] Mobile dashboard: disable pinch-zoom, limit text selection on UI chrome
- [ ] Support for multiple Sonos rooms without env var mapping (future)

### Deferred (v2+)

- [ ] Configurable per-category toggle UI (drug / sexual / profanity on/off) — profiles partially address this
- [ ] Per-room profile assignment (Living Room vs. Office) — PROF-05
- [ ] Custom profile creation (user-defined thresholds, not just presets) — PROF-06
- [ ] Per-child profiles or age-based filtering tiers

### Out of Scope

- Signal bot notifications — replaced by web dashboard (D-01, D-02 in Phase 3 context)
- Apple Music support — Spotify only for v1
- Sonos auto-activation of FSM — manual toggle first
- iOS native app — web dashboard covers the use case
- Sentiment NLP — too complex for v1; layered approach ships value first
- Severity scoring within content categories

## Context

- **Shipped v1.4** on 2026-04-05: 3 phases (14–16), 7 plans — idle detection, skip history persistence, and filter profiles with split-button dashboard UI
- **Shipped v1.3** on 2026-04-04: 13 phases total, drug/sexual reference detection pipeline + incident log propagation + dashboard badge variants; title-fallback scan added
- **Shipped v1.2** on 2026-04-03: 9 phases total, 23 plans, ~1,754 lines (Python + HTML/CSS/JS + tests)
- Tech stack: Python 3.12, asyncio, spotipy, SoCo, FastAPI, SSE, LRCLIB, better-profanity, Docker, pytest; vanilla JS frontend (no framework)
- Codebase: ~3,931 lines Python, 904 lines HTML/CSS/JS
- Sonos SSDP auto-discovery via `probe_sonos_speakers()` at startup; `SONOS_SPEAKER_IPS=Name=IP,...` is explicit escape hatch for LXC/Proxmox hosts
- Sonos in Spotify Connect mode returns error 701 on UPnP `next()` — daemon falls back to Spotify API
- Docker healthcheck: `poll_loop()` touches `/app/.healthcheck` every cycle; 90s hang detection (interval 30s × retries 3)
- Children are ages 3 and 7 — filtering errs on the side of caution
- Music plays through Living Room Sonos (192.168.1.164); Dining Room IP unknown (offline)
- setup_auth.py requires scope `user-read-playback-state user-read-currently-playing user-modify-playback-state` — all three needed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Signal bot → Web dashboard | Signal bot scope too broad for v1; web dashboard simpler and sufficient | ✓ Good — dashboard works well |
| SoCo for Sonos + Spotify API fallback | Sonos is_restricted=True blocks Web API; SoCo handles UPnP directly | ✓ Good — fallback handles Spotify Connect edge case |
| File-based IPC (skip_events.jsonl) | In-process asyncio.Queue doesn't cross Docker container boundary | ✓ Good — file tail reliable |
| SONOS_SPEAKER_IPS env var | SSDP multicast blocked by host firewall; direct IP bypasses discovery | ✓ Good — now escape hatch; SSDP is primary |
| Pause on 5th skip instead of skip+pause | Race condition: skip moves track before pause fires | ✓ Good — pause on current track works reliably |
| Manual FSM toggle | Simplest v1; auto-detect Sonos is v2 | ✓ Good |
| Explicit flag + lyric scan | Sentiment analysis complex; layered approach ships incrementally | ✓ Good |
| Touch-file healthcheck probe | Simplest cross-language probe; mtime check catches hung event loop | ✓ Good — verified working |
| PROXMOX.md as separate file | Keeps README minimal; LXC multicast edge case is niche enough to warrant dedicated doc | ✓ Good |
| 3-section README (Quick Start / Prerequisites / Updating) | Minimal surface area; no troubleshooting section forces good defaults | ✓ Good |
| SSE + now_playing.json dual delivery | SSE for real-time updates; file snapshot for page-load hydration — decoupled | ✓ Good — hydration on reconnect works reliably |
| Shared token cache volume (daemon ↔ web_ui) | web_ui spotipy reuses daemon OAuth token via Docker volume; no second auth flow needed | ✓ Good — single `make auth` covers both containers |
| Manual skip bypasses consecutive-skip counter | Parent intent is deliberate; counter is for algorithmic cascade detection only | ✓ Good — correct semantics |
| severity=0 sentinel for non-profanity-scan branches | eval_result always includes severity field; frontend can rely on it always being present | ✓ Good |
| Multi-badge flex container (badge-group) | Additive badge pattern extensible for drug/sexual badges | ✓ Good — groundwork laid |
| OAuth scope missing user-read-playback-state | setup_auth.py originally requested wrong scope | ⚠ Fixed — update setup_auth.py and re-run make auth on existing installs |
| TrackEvalResult frozen dataclass | Positional 3-tuple fragile as fields grow; named dataclass prevents positional errors | ✓ Good — zero positional unpacks remain |
| No-short-circuit scan contract | All three scanners always run before priority decision | ✓ Good — enforced by test |
| SEXUAL_TERMS disjoint from SEVERITY_MAP | Overlap would cause double-counting and incorrect severity scores | ✓ Good — enforced by unit test |
| Title+artist fallback scan when lyrics unavailable | Tracks with no lyrics bypassed all scanning; title scan catches obvious cases | ✓ Good |
| Event IDs for dedup | Monotonic integer event IDs enable robust SSE reconnect merge without UUID overhead | ✓ Good — counter survives restart via file scan |
| GET /feed endpoint for history | File-read endpoint decouples history from SSE stream (_file_tail stays at EOF) | ✓ Good — consistent with /now-playing hydration pattern |
| Idle debounce counter + dedup flag | 3-poll threshold prevents false idle on brief Spotify polling gaps; dedup flag ensures single SSE event per transition | ✓ Good — no false idles in testing |
| PROFILE_MAP + _build_content_checker() | Scanner objects are long-lived; only ContentChecker wrapper reconstructed on profile change — avoids re-initializing heavy scanners | ✓ Good — zero regression; explicit_skip defaults True |
| explicit_skip: bool = True default | Preserves all existing Tier 1 skip behavior by default; profiles opt out explicitly | ✓ Good — zero regression |
| Split-button (left=FSM toggle, right=▾ dropdown) | Separates two orthogonal controls (on/off vs. which profile) into one compact compound element | ✓ Good — verified intuitive in UAT |
| Dropdown closes on SSE disconnect (not reconnect) | User expects dropdown to close when connection drops, not after it restores — avoids stale open state | ✓ Good — user-verified |

---
## Current Milestone: v1.5 Dashboard Polish & Mobile UX

**Goal:** Polish the dashboard with mobile-friendly behavior, per-profile transparency, and a rebrand to "Read the Room."

**Target features:**
- Rebrand to "Read the Room" (UI strings, README, project docs)
- Info icon per filter profile showing what content each one skips
- Mobile friendliness: disable zoom, limit text selection on UI chrome

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after v1.5 milestone start — Dashboard Polish & Mobile UX.*
