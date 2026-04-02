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

### Active

- [ ] Sonos SSDP discovery works without manual IP configuration (firewall/multicast issue)
- [ ] Support for multiple Sonos rooms without env var mapping
- [ ] Project has a complete clone-and-run README usable by anyone with Docker
- [ ] Service survives host reboots without manual intervention

### Deferred (v2+)

- [ ] Sentiment analysis for adult themes (depression, violence, drug use)
- [ ] Per-child profiles or age-based filtering tiers

### Out of Scope

- Signal bot notifications — replaced by web dashboard (D-01, D-02 in Phase 3 context)
- Apple Music support — Spotify only for v1
- Sonos auto-activation of FSM — manual toggle first
- iOS native app — web dashboard covers the use case
- Sentiment NLP — too complex for v1; layered approach ships value first

## Context

- **Shipped v1.0** on 2026-04-02: 3 phases, 14 plans, ~1,500 LOC Python
- Tech stack: Python 3.12, asyncio, spotipy, SoCo, FastAPI, aiosqlite, LRCLIB, better-profanity, Docker
- Sonos SSDP auto-discovery via `probe_sonos_speakers()` at startup; `SONOS_SPEAKER_IPS` is now fallback/escape hatch (Phase 4 complete 2026-04-02)
- Sonos in Spotify Connect mode returns error 701 on UPnP `next()` — daemon falls back to Spotify API
- Children are ages 3 and 7 — filtering errs on the side of caution
- Music plays through Living Room Sonos (192.168.1.164); Dining Room IP unknown (offline)

## Current Milestone: v1.1 Deployment

**Goal:** Make the project easy to clone and run on any Docker host, fix Sonos SSDP discovery so manual IP mapping isn't required, and verify boot persistence.

**Target features:**
- Sonos SSDP auto-discovery (diagnose multicast block; `SONOS_SPEAKER_IPS` becomes fallback only)
- Boot persistence verified and documented (`systemctl enable docker` + `restart:always`)
- Clone-and-run README (env setup, OAuth flow, Sonos network requirements, Proxmox/LXC notes)
- `docker-compose.yml` healthcheck for silent hang detection

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Signal bot → Web dashboard | Signal bot scope too broad for v1; web dashboard simpler and sufficient | ✓ Good — dashboard works well |
| SoCo for Sonos + Spotify API fallback | Sonos is_restricted=True blocks Web API; SoCo handles UPnP directly | ✓ Good — fallback handles Spotify Connect edge case |
| File-based IPC (skip_events.jsonl) | In-process asyncio.Queue doesn't cross Docker container boundary | ✓ Good — file tail reliable |
| SONOS_SPEAKER_IPS env var | SSDP multicast blocked by host firewall; direct IP bypasses discovery | ✓ Good — immediate fix |
| Pause on 5th skip instead of skip+pause | Race condition: skip moves track before pause fires | ✓ Good — pause on current track works reliably |
| Manual FSM toggle | Simplest v1; auto-detect Sonos is v2 | ✓ Good |
| Explicit flag + lyric scan | Sentiment analysis complex; layered approach ships incrementally | ✓ Good |

## Evolution

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 after Phase 4 complete — Sonos discovery hardening*
