# Roadmap: Spotify Family Safe Mode

## Overview

Three phases deliver a working family-safe Spotify daemon. Phase 1 establishes the authenticated poll loop — the skeleton everything attaches to. Phase 2 builds the content filter and auto-skip on top of that loop, which is the product's core value. Phase 3 closes the loop with Signal notifications and interactive confirmations, making the system observable and controllable without touching the server.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Daemon & Spotify Auth** - Authenticated poll loop running as a Docker service with restart:always; detects track changes (completed 2026-04-01)
- [ ] **Phase 2: Content Filtering & Auto-Skip** - Three-tier filter (explicit flag → LRCLIB → profanity scan) with dual skip path (SoCo + Spotify API) and Family Safe Mode toggle
- [ ] **Phase 3: Signal Notifications & Interactive Confirmations** - Skip notifications and allow/skip prompts via Signal; 5-skip playlist prompt

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
- [ ] 02-02-PLAN.md — LyricsService (LRCLIB fetch + SQLite cache), ProfanityScanner (severity mapping + leet-speak), full pipeline wiring
**UI hint**: no

### Phase 3: Signal Notifications & Interactive Confirmations
**Goal**: Every automatic skip and every ambiguous track generates a Signal message; the user can reply to ambiguous prompts in real-time and the daemon acts on the reply within 30 seconds
**Depends on**: Phase 2
**Requirements**: FSM-03, SIG-01, SIG-02, SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. When a track is auto-skipped, a Signal DM arrives within a few seconds showing the track name, artist, and skip reason
  2. When an ambiguous track plays (lyrics unavailable), a Signal DM arrives asking "Allow or Skip?" and replying "allow" lets the track play; replying "skip" skips it
  3. If no reply arrives within 30 seconds, the ambiguous track is skipped automatically and a Signal message confirms the timeout action
  4. After 5 consecutive skips, a Signal message prompts the user to consider switching playlist or radio
  5. Restarting the signal-cli-rest-api Docker container and then triggering a skip produces a delivered Signal notification (WebSocket reconnects without daemon restart)
**Plans**: TBD

Plans:
- [ ] 03-01-PLAN.md — signal-cli-rest-api Docker setup, device linking, SignalNotifier HTTP send, skip notification integration
- [ ] 03-02-PLAN.md — WebSocket receive loop, pending-confirmation map, 30s timeout, 5-skip prompt, reconnect logic

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | 2/2 | Complete   | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | 1/2 | In Progress|  |
| 3. Signal Notifications & Interactive Confirmations | 0/2 | Not started | - |
