# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-02
**Phases:** 3 | **Plans:** 14 | **LOC:** ~1,500 Python

### What Was Built

- Asyncio daemon polling Spotify every 1s — detects track changes, checks explicit flag, fetches lyrics from LRCLIB, scans for profanity with leet-speak handling
- Dual skip path: SoCo UPnP for Sonos speakers (`is_restricted=True`), Spotify Web API for everything else; fallback from SoCo to Spotify API on error 701
- FastAPI web UI with real-time SSE skip feed, FSM toggle, and 5-skip pause warning banner — served in Docker alongside the daemon
- File-based IPC (`skip_events.jsonl`) between daemon and web_ui containers — replaces broken cross-process asyncio.Queue
- `SONOS_SPEAKER_IPS` env var to bypass SSDP multicast discovery blocked by host firewall
- Group coordinator routing in SoCo (`_soco_next` / `_soco_pause`) — fixes UPnP error 701 when Sonos is in Spotify Connect mode

### What Worked

- **GSD coarse granularity** — 14 plans across 3 phases kept plans focused and parallelizable; no plan was too large to execute atomically
- **SkipClient ABC** — isolating skip logic behind an interface meant daemon.py never needed changing when SoCo edge cases were discovered; just add methods to the implementations
- **File-based IPC** — the simplest cross-container solution; no Redis, no broker, just a jsonl tail. Proven immediately reliable
- **`SONOS_SPEAKER_IPS` env var** — immediately unblocked Sonos testing without touching firewall config; fits naturally into Docker's env_file pattern
- **Debugging with notes + debug files** — capturing root causes in `.planning/debug/` during investigation saved re-diagnosing the same issue

### What Was Inefficient

- **Signal bot scope pivot** — Phase 3 was originally "Signal notifications + interactive confirmations"; Signal bot was cut mid-phase when the web dashboard proved simpler. A clearer v1 scoping discussion upfront would have saved planning overhead
- **In-process queue assumption** — the SSE queue was initially designed as an in-process asyncio.Queue; the Docker container boundary wasn't caught until integration. File-tail was the right design from the start given docker-compose
- **SSDP firewall issue discovered late** — Sonos discovery only failed at runtime; the host firewall blocking multicast wasn't caught in planning. A `SONOS_SPEAKER_IPS` escape hatch should have been in Phase 2 from day 1
- **`save_state()` read-merge** — the race between daemon writes and FSM toggle writes required adding a read-merge pattern mid-phase; this is a known pattern for any shared-file state and should be a default

### Patterns Established

- **SkipClient ABC** — all future transport integrations (Bridge, AirPlay, etc.) add a new class implementing the same `skip()` / `pause()` interface; daemon.py stays clean
- **File-based IPC with jsonl** — event logs as append-only jsonl files tailed by consumers; works across process and container boundaries; naturally persistent
- **read-merge-write for state.json** — any writer loads the current disk state, merges its fields, then writes; prevents clobbering unrelated keys
- **GSD debug notes** — whenever a non-obvious root cause is found, capture it in `.planning/debug/` before fixing; prevents re-investigation in future sessions
- **env var escape hatches for hardware** — any hardware discovery mechanism (Sonos SSDP, mDNS, etc.) should have a manual IP/address override env var from day 1

### Key Lessons

1. **Design for the Docker boundary from the start** — asyncio coroutines don't cross container walls; assume file or socket IPC for any multi-service architecture
2. **Hardware discovery is optional, not required** — always provide a manual override for any network discovery mechanism; discovery is an optimization, not a dependency
3. **Group coordinator routing is mandatory for Sonos groups** — any UPnP transport command must target the group coordinator, not an arbitrary group member; build this in, not as a hotfix
4. **Explicit flag + lyric scan is the right layered strategy** — fast path (explicit flag) handles the common case in zero network time; lyric scan catches the gaps; sentiment analysis is v2
5. **Phase scope creep signals a scope conversation, not a code fix** — when a phase's original goal (Signal bot) conflicts with a simpler alternative (web dashboard), pause and re-scope rather than building both

### Cost Observations

- Model mix: primarily Sonnet 4.6 (GSD balanced profile)
- Sessions: ~8 sessions over 2 days (2026-04-01 → 2026-04-02)
- Notable: coarse granularity (14 plans / 3 phases) kept each session focused; no context overflow events

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~8 | 3 | First milestone; GSD coarse granularity established |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|--------------------|
| v1.0 | manual UAT | — | 0 (all deps intentional) |

### Top Lessons (Verified Across Milestones)

1. Design for the container/process boundary from day 1 — asyncio queues don't cross walls
2. Hardware discovery needs manual override escape hatches from day 1
