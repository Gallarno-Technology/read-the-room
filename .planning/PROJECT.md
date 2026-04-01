# Spotify Family Safe Mode

## What This Is

A background service running on a home server that monitors Spotify playback and automatically skips songs that violate family-safe content rules when Family Safe Mode is active. It uses Spotify's explicit flag and lyric scanning to filter content, sends skip notifications and confirmation requests via Signal, and integrates with Sonos speakers as the "public device" signal. Built for a parent who wants to listen freely but not expose young children (ages 3 and 7) to explicit lyrics, heavy curse words, or adult themes.

## Core Value

Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can toggle Family Safe Mode on/off
- [ ] Service monitors currently playing Spotify track in real-time
- [ ] Songs marked explicit by Spotify are auto-skipped
- [ ] Songs with curse words detected in lyrics are auto-skipped
- [ ] Ambiguous songs trigger a Signal notification asking user to confirm skip or allow
- [ ] Auto-skipped songs always send a Signal notification (what was skipped and why)
- [ ] After 5 consecutive skips, Signal notification prompts user to switch playlist/radio
- [ ] Service runs continuously on a home server (always-on Mac)
- [ ] Notifications and controls delivered via existing Signal bot

### Out of Scope

- Apple Music support — v1 Spotify only; architecture should not preclude adding it later
- Sonos auto-detection of Family Safe Mode — manual toggle first; auto-detect is v2
- Sentiment analysis for adult themes (depression, suicide, drug use) — v2; requires more sophisticated NLP
- iOS native app — Signal bot covers notifications for v1
- Web dashboard — not needed if Signal bot handles all interaction
- Per-child profiles or age-based filtering tiers — out of scope for v1

## Context

- User exclusively uses Spotify for music playback
- Music plays through Sonos speakers at home (the "public device")
- User already has a Signal bot account set up and configured
- Home server / always-on Mac will host the service
- Children are ages 3 and 7 — filtering should err on the side of caution
- Lyric data will require a third-party lyrics API (Spotify does not provide lyrics via their API)
- Spotify Web API supports track metadata, playback state polling, and skip controls via the playback endpoint
- Future v2: auto-activate Family Safe Mode when Sonos is detected as the active playback device

## Constraints

- **Integration**: Spotify Web API only — no scraping, no unofficial endpoints
- **Lyrics**: Third-party lyrics API needed (Genius, Musixmatch, or similar) — subject to rate limits and coverage gaps
- **Notifications**: Signal bot (pre-configured) — no other notification channel for v1
- **Runtime**: Home server / always-on Mac — service must be lightweight and self-healing (auto-restart on crash)
- **Latency**: Skip must happen fast enough that children don't hear more than a second or two of a violating song
- **Privacy**: Lyrics and song data should not be persisted beyond what's needed for filtering

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Signal bot for notifications | Already set up, zero friction, real push on mobile | — Pending |
| Home server deployment | Free, private, no cloud dependency | — Pending |
| Manual toggle for Family Safe Mode | Simplest v1; auto-detect Sonos is v2 | — Pending |
| Explicit flag + lyric scan for v1 | Sentiment analysis is complex; layered approach ships value incrementally | — Pending |

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
*Last updated: 2026-04-01 after initialization*
