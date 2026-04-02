# Roadmap: Spotify Family Safe Mode

## Overview

Three phases deliver a working family-safe Spotify daemon. Phase 1 establishes the authenticated poll loop — the skeleton everything attaches to. Phase 2 builds the content filter and auto-skip on top of that loop, which is the product's core value. Phase 3 closes the loop with a Web UI dashboard — a real-time skip feed and FSM toggle served by FastAPI — making the system observable and controllable without touching the server.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Daemon & Spotify Auth** - Authenticated poll loop running as a Docker service with restart:always; detects track changes (completed 2026-04-01)
- [x] **Phase 2: Content Filtering & Auto-Skip** - Three-tier filter (explicit flag → LRCLIB → profanity scan) with dual skip path (SoCo + Spotify API) and Family Safe Mode toggle (completed 2026-04-02)
- [ ] **Phase 3: Web UI Dashboard** - Real-time skip history feed and FSM toggle via FastAPI + plain HTML/JS + SSE; 5-consecutive-skip pause; dismissible warning banner

## Phase Details

### Phase 1: Core Daemon & Spotify Auth
**Goal**: A daemon runs continuously on the home server (Proxmox/Arch Linux Docker), authenticates with Spotify via terminal OAuth, and correctly detects the currently playing track every ~1 second
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up -d` starts the daemon; `docker compose logs -f daemon` shows a track name + artist + explicit flag within ~1 second of a track change
  2. After the one-time `python setup_auth.py` terminal OAuth step, the daemon restarts and operates headlessly with no browser or re-authentication required
  3. Running `docker compose stop` stops the daemon cleanly within 1-2 seconds (SIGTERM delivered via exec-form CMD); `docker compose up -d` resumes polling automatically
  4. `state.json` exists on disk and persists the last track ID across container restarts and rebuilds
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — OAuth setup script (setup_auth.py), requirements.txt, .env.example, Dockerfile, docker-compose.yml
- [x] 01-02-PLAN.md — Asyncio poll loop (daemon.py), track-change detection, 429 backoff, graceful shutdown, state.json

### Phase 2: Content Filtering & Auto-Skip
**Goal**: When Family Safe Mode is on, tracks that violate family-safe rules are automatically skipped — via SoCo for Sonos speakers, Spotify API for all other devices — before children hear more than a second or two
**Depends on**: Phase 1
**Requirements**: FILT-01, FILT-02, FILT-03, FILT-04, FILT-05, FILT-06, SKIP-01, SKIP-02, SKIP-03, FSM-01, FSM-02
**Success Criteria** (what must be TRUE):
  1. Playing an explicit-flagged track with Family Safe Mode on causes it to be skipped within 1-2 seconds of starting; a log entry shows the reason as "explicit flag"
  2. Playing a non-explicit track with profanity in the lyrics causes a skip within a few seconds; the log shows "profanity detected"
  3. Playing an instrumental or lyrics-unavailable track with Family Safe Mode on does NOT cause a skip
  4. Toggling Family Safe Mode off (editing `state.json` or via a toggle command) causes explicit and profane tracks to play through without skipping
  5. Tracks that were already fetched from LRCLIB on a previous play are served from the SQLite cache on repeat plays (observable via log showing "cache hit")
  6. Tracks playing on Sonos skip without error; tracks playing on non-Sonos devices skip via the Spotify API
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — SkipClient interface (SoCo + Spotify), ContentChecker with explicit-flag tier, FSM toggle, daemon.py integration, OAuth scope expansion
- [x] 02-02-PLAN.md — LyricsService (LRCLIB fetch + SQLite cache), ProfanityScanner (severity mapping + leet-speak), full pipeline wiring
**UI hint**: no

### Phase 3: Web UI Dashboard
> **Scope change from original:** Signal notifications dropped entirely (see 03-CONTEXT.md D-01). Phase delivers a FastAPI + plain HTML/JS Web UI dashboard. Requirements SIG-01–SIG-04 and FSM-03 are remapped to Web UI equivalents.

**Goal**: A browser-accessible dashboard at http://localhost:8888 shows a real-time skip history feed (what was skipped, when, and why) and a Family Safe Mode toggle — no server access required for day-to-day operation
**Depends on**: Phase 2
**Requirements**: FSM-03, SIG-01, SIG-02, SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. Visiting http://localhost:8888 shows the dashboard with an FSM toggle button and an "Incident Log" section
  2. When a track is auto-skipped, a new entry appears in the skip feed within seconds (track name, artist, reason badge, timestamp) — no page refresh needed
  3. Clicking the FSM toggle flips Family Safe Mode on/off; the daemon picks up the change within one poll cycle
  4. After 5 consecutive skips, Spotify playback pauses automatically and a warning banner appears in the dashboard
  5. Dismissing the warning banner hides it; it reappears if 5 more consecutive skips occur
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — daemon.py skip event queue + 5-skip counter/pause, FastAPI web_ui service (SSE /events, POST /fsm, GET /fsm)
- [ ] 03-02-PLAN.md — Dashboard HTML/CSS/JS template (FSM toggle, skip feed, badges, banner, SSE status), web_ui Dockerfile, docker-compose web_ui service, Makefile ui-logs target

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | 2/2 | Complete   | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | 7/7 | Complete   | 2026-04-02 |
| 3. Web UI Dashboard | 1/2 | In Progress|  |
