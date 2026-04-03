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

### Active

- [ ] Drug reference detection in lyrics (boolean signal)
- [ ] Sexual content detection in lyrics (boolean signal)
- [ ] Both signals logged in incident log alongside existing flags
- [ ] Support for multiple Sonos rooms without env var mapping
- [ ] Dashboard shows current track with real-time filter evaluation state
- [ ] Parent can manually skip current track from dashboard without opening Spotify

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

- **Shipped v1.1** on 2026-04-02: 5 phases total, 18 plans, ~1,213 lines (Python + YAML + docs)
- Tech stack: Python 3.12, asyncio, spotipy, SoCo, FastAPI, aiosqlite, LRCLIB, better-profanity, Docker, pytest
- Sonos SSDP auto-discovery via `probe_sonos_speakers()` at startup; `SONOS_SPEAKER_IPS=Name=IP,...` is explicit escape hatch for LXC/Proxmox hosts
- Sonos in Spotify Connect mode returns error 701 on UPnP `next()` — daemon falls back to Spotify API
- Docker healthcheck: `poll_loop()` touches `/app/.healthcheck` every cycle; 90s hang detection (interval 30s × retries 3)
- Children are ages 3 and 7 — filtering errs on the side of caution
- Music plays through Living Room Sonos (192.168.1.164); Dining Room IP unknown (offline)

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

## Planned Milestone: v1.2 Now Playing Status

**Goal:** Dashboard shows the current track with its real-time filter evaluation state and a manual skip button, so parents can see what's playing and act on it without opening Spotify.

**Target features:**
- Now-playing card: track name, artist, evaluation state badge (evaluating → passed / no-lyrics / skipped)
- "Evaluating" is always the initial state on every new track — Spotify/Sonos API latency means no instant result is reliable
- Manual skip button — triggers skip from web UI without duplicating Spotify auth
- Album artwork — nice-to-have, not a requirement
- Current track only — existing skip feed history unchanged

## Current Milestone: v1.3 Drug & Sexual Reference Detection

**Goal:** Extend the filter pipeline with two new discrete content signals — drug references and sexual content — detected from lyrics already fetched by LRCLIB, sitting alongside the existing explicit flag and profanity layers.

**Target features:**
- Drug reference detection against LRCLIB lyrics (boolean signal)
- Sexual content detection against LRCLIB lyrics (boolean signal)
- Both signals logged in incident log alongside existing flags
- Independent named booleans on track evaluation result (structured for per-category UI toggles next milestone)
- Detection method within existing pipeline — no LLM integration required

## Evolution

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 — v1.3 Drug & Sexual Reference Detection milestone started; v1.2 Now Playing Status restored*
