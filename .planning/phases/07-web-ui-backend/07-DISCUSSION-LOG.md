# Phase 7: Web UI Backend - Discussion Log (Discuss Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-03
**Phase:** 07-web-ui-backend
**Mode:** discuss
**Areas analyzed:** Now Playing Endpoint, Skip Endpoint, Spotipy Auth

## Gray Areas Identified

| Area | Confidence | Resolution |
|------|-----------|------------|
| Idle response shape | Likely | Auto-decided (recommendation) |
| POST /skip error contract | Likely | Auto-decided (recommendation) |
| Stale now_playing.json | Unclear | User discussion |

## Assumptions Presented

### Now Playing Endpoint
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Return `{"status": "idle"}` when file missing | Likely | Success criteria says "defined idle response" but no shape given; sentinel is simplest |
| Return file contents as-is (no staleness detection) | Unclear | File persists across daemon restarts; timestamp-based detection has false positives |

### Skip Endpoint
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| SKIP-03 satisfied architecturally | Confident | `consecutive_skips` is in-memory in `poll_loop()` — web_ui bypass is the architecture |
| 503 + JSON body on Spotify error | Likely | Phase 8 needs failure signal; 503 is conventional for upstream unavailability |

### Spotipy Auth
| Assumption | Confident | Evidence |
|------------|-----------|----------|
| Missing `token_cache` volume mount in web_ui | Confident | `docker-compose.yml` web_ui volumes: only `state.json` and `data/` mounted |
| Same `SpotifyOAuth` + `CacheFileHandler` pattern | Confident | `daemon.py` lines 432–441; SPOTIFY_CACHE_PATH already in `.env` |
| Same scope as daemon | Likely | Narrower scope risks token scope narrowing on auto-refresh |

## User Discussion

### Stale now_playing.json

**Question:** When the daemon is stopped or Spotify is idle, now_playing.json persists with last track. What should GET /now-playing do?

**Options presented:**
1. Return as-is (recommended) — Phase 8's SSE disconnect is the staleness signal
2. Detect staleness by timestamp age — fragile for long tracks
3. Add daemon heartbeat field — requires Phase 6 changes (out of scope)

**User chose:** Return as-is

**Captured as:** D-03 — return file contents verbatim; no staleness detection

## Corrections Applied

None — all other assumptions confirmed via recommendation defaults.
