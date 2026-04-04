# Spotify Family Safe Mode

## What This Is

A background service running on a home server that monitors Spotify playback and automatically skips songs that violate family-safe content rules when Family Safe Mode is active. It uses Spotify's explicit flag and lyric scanning (via LRCLIB) to filter content, with a real-time web dashboard for monitoring and control. Integrates with Sonos speakers via SoCo UPnP and Spotify Web API. Built for a parent who wants to listen freely but not expose young children (ages 3 and 7) to explicit lyrics or heavy curse words.

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
- ✓ When lyrics unavailable, scan track title + artist before allowing — v1.3 (quick task)

### Active

- [ ] Support for multiple Sonos rooms without env var mapping (future)

### Deferred (v2+)

- [ ] Configurable per-category toggle UI (drug / sexual / profanity on/off)
- [ ] Per-child profiles or age-based filtering tiers
- [ ] Severity scoring within content categories

### Out of Scope

- Signal bot notifications — replaced by web dashboard (D-01, D-02 in Phase 3 context)
- Apple Music support — Spotify only for v1
- Sonos auto-activation of FSM — manual toggle first
- iOS native app — web dashboard covers the use case
- Sentiment NLP — too complex for v1; layered approach ships value first

## Context

- **Shipped v1.3** on 2026-04-04: 13 phases total, 8 plans (v1.3), drug/sexual reference detection pipeline + incident log propagation + dashboard badge variants; title-fallback scan added as quick task
- **Shipped v1.2** on 2026-04-03: 9 phases total, 23 plans, ~1,754 lines (Python + HTML/CSS/JS + tests)
- Tech stack: Python 3.12, asyncio, spotipy, SoCo, FastAPI, SSE, LRCLIB, better-profanity, Docker, pytest; vanilla JS frontend (no framework)
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
| Touch-file healthcheck probe | Simplest cross-language probe; mtime check catches hung event loop (process alive but deadlocked) | ✓ Good — verified working |
| PROXMOX.md as separate file | Keeps README minimal; LXC multicast edge case is niche enough to warrant dedicated doc | ✓ Good |
| 3-section README (Quick Start / Prerequisites / Updating) | Minimal surface area; no troubleshooting section forces good defaults over workarounds | ✓ Good |
| SSE + now_playing.json dual delivery | SSE for real-time updates; file snapshot for page-load hydration — decoupled, no shared state between containers | ✓ Good — hydration on reconnect works reliably |
| Shared token cache volume (daemon ↔ web_ui) | web_ui spotipy reuses daemon OAuth token via Docker volume; no second auth flow needed | ✓ Good — single `make auth` covers both containers |
| Manual skip bypasses consecutive-skip counter | Parent intent is deliberate; counter is for algorithmic cascade detection only | ✓ Good — correct semantics |
| severity=0 sentinel for non-profanity-scan branches | eval_result always includes severity field; frontend can rely on it always being present | ✓ Good — frontend never gets KeyError |
| Multi-badge flex container (badge-group) | Additive badge pattern: eval_state badge + criteria badges; extensible for v1.3 drug/sexual badges | ✓ Good — groundwork laid for v1.3 |
| OAuth scope missing user-read-playback-state | setup_auth.py originally requested wrong scope; sp.current_playback() requires user-read-playback-state not user-read-currently-playing | ⚠ Fixed — update setup_auth.py and re-run make auth on existing installs |
| TrackEvalResult frozen dataclass | Positional 3-tuple is fragile as fields grow; named dataclass with keyword-only construction prevents positional errors | ✓ Good — zero positional unpacks remain |
| No-short-circuit scan contract | All three scanners (profanity, drug, sexual) always run before priority decision; prevents false "all-clear" when multiple signals fire | ✓ Good — enforced by test_all_signals_fire_all_scans_run |
| SEXUAL_TERMS disjoint from SEVERITY_MAP | Overlap would cause terms to be counted twice and produce incorrect severity scores | ✓ Good — enforced by first-position unit test |
| severity=0 sentinel for drug/sexual skip branches | eval_result always includes severity field; frontend never gets KeyError regardless of which scanner fired | ✓ Good — consistent with profanity sentinel pattern |
| Title+artist fallback scan when lyrics unavailable | Tracks with no lyrics (e.g., "Cocaine") bypassed all scanning; title scan catches obvious cases before returning lyrics_unavailable | ✓ Good — catches high-signal titles at zero lyric cost |
| Drug/sexual badge labels: no "Flagged:" prefix | "Drug reference" and "Sexual content" are self-explanatory; prefix adds noise without clarity | ✓ Good — consistent with explicit badge label pattern |

## Current Milestone: v1.4 Dashboard Polish & Filter Profiles

**Goal:** Make the dashboard accurately reflect real playback state, preserve skip history across reconnects, and replace the hardcoded filter with named UI-selectable profiles.

**Target features:**
- Skip history survives page refresh and SSE reconnect (SEED-007)
- Now-playing card clears to idle when playback stops (SEED-008)
- Filter profile selector in dashboard — 4 named presets; FSM toggle still gates on/off, profile controls which rules apply (SEED-005)

**Filter profiles:**
- Family Friendly: explicit skip, profanity ≥ severity 2, drug skip, sexual skip
- Adult but Wholesome: explicit skip, profanity ≥ severity 3, drug allow, sexual skip
- Adult, No Sexual: explicit allow, profanity allow, drug allow, sexual skip
- Not Explicit: explicit skip only, all lyric scanning off

## Evolution

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-04 after Phase 14 (idle-detection) complete — dashboard now shows idle state when nothing is playing.*
