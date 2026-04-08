# Architecture Research

**Domain:** OSS release preparation — Python/Docker home automation daemon
**Researched:** 2026-04-06
**Confidence:** HIGH — findings based on direct inspection of live codebase, git history, and tracked file inventory

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Docker host (network_mode: host)                │
│                                                                  │
│  ┌──────────────────────┐   ┌──────────────────────────────┐    │
│  │  daemon container    │   │  web_ui container            │    │
│  │  (Python asyncio)    │   │  (FastAPI / uvicorn :8888)   │    │
│  │                      │   │                              │    │
│  │  - poll_loop()       │   │  - GET  /                    │    │
│  │  - ContentChecker    │   │  - GET  /now-playing         │    │
│  │  - SocoSkipClient    │   │  - POST /skip                │    │
│  │  - SpotifySkipClient │   │  - GET  /fsm                 │    │
│  │  - LyricsService     │   │  - POST /fsm                 │    │
│  │  - probe_sonos()     │   │  - GET  /profile             │    │
│  └──────┬───────────────┘   │  - POST /profile             │    │
│         │                   │  - GET  /feed (SSE)          │    │
│         │  File-based IPC   └──────────┬───────────────────┘    │
│         │  (bind-mount ./data/)        │                        │
│         ▼                             ▼                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ./data/events.jsonl     (skip event log, append-only)  │    │
│  │  ./data/now_playing.json (hydration snapshot)           │    │
│  │  ./state.json            (FSM toggle + active profile)  │    │
│  │  ./token_cache/.cache    (OAuth token — shared volume)  │    │
│  │  ./lyrics_cache.db       (SQLite — LRCLIB cache)        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  External: Spotify Web API, Sonos UPnP (SSDP / direct IP)       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| daemon | Poll Spotify, evaluate content, skip via SoCo or Spotify API, write events | `daemon.py` |
| web_ui | Serve dashboard, expose REST + SSE endpoints, read/write state.json | `web_ui/main.py` |
| ContentChecker | Orchestrate profanity/drug/sexual scanners, apply active profile rules | `content_checker.py` |
| LyricsService | Fetch LRCLIB lyrics, cache in SQLite, fallback gracefully | `lyrics_service.py` |
| SocoSkipClient | Skip/pause via SoCo UPnP; fallback to Spotify API on error 701 | `skip_client.py` |
| SpotifySkipClient | Skip via Spotify Web API (non-Sonos devices or fallback) | `skip_client.py` |
| scanners | Profanity/drug/sexual term detection against lyric text | `profanity_scanner.py`, `drug_scanner.py`, `sexual_content_scanner.py` |

---

## Recommended Project Structure (for OSS Release)

The existing flat layout is appropriate for a single-purpose daemon. No restructuring is needed. The value is in documenting this clearly for contributors.

```
read-the-room/              # repo root (rename from spotify-sentiment recommended)
├── daemon.py               # core async polling daemon — entry point for daemon container
├── content_checker.py      # content evaluation orchestrator
├── lyrics_service.py       # LRCLIB fetch + SQLite cache
├── skip_client.py          # SoCo and Spotify skip abstractions
├── profanity_scanner.py    # profanity detection with severity scoring
├── drug_scanner.py         # drug reference detection
├── sexual_content_scanner.py # sexual content detection
├── setup_auth.py           # one-time Spotify OAuth helper
├── requirements.txt        # daemon Python dependencies
├── Dockerfile              # daemon image
├── docker-compose.yml      # two-service orchestration
├── Makefile                # dev shortcuts (setup, auth, up, down, logs)
├── .env.example            # template — the only secrets file tracked in repo
├── .gitignore              # excludes .env, state.json, token_cache/, data/, lyrics_cache.db
├── README.md               # public-facing quick-start
├── PROXMOX.md              # LXC multicast edge-case notes
├── LICENSE                 # MISSING — must add before public release
├── CONTRIBUTING.md         # MISSING — must add before public release
├── tests/
│   ├── conftest.py
│   ├── test_content_checker.py
│   ├── test_daemon_events.py
│   ├── test_drug_scanner.py
│   ├── test_feed_endpoint.py
│   ├── test_healthcheck.py
│   ├── test_info_icon.py
│   ├── test_mobile_polish.py
│   ├── test_sexual_content_scanner.py
│   ├── test_skip_client.py
│   ├── test_sonos_probe.py
│   └── test_web_ui_endpoints.py
└── web_ui/
    ├── main.py             # FastAPI app
    ├── requirements.txt    # web_ui Python dependencies (separate from daemon)
    ├── Dockerfile          # web_ui image
    ├── __init__.py
    └── templates/
        └── index.html      # single-page dashboard (vanilla JS, SSE)
```

### Structure Rationale

- **Flat root layout:** All daemon Python modules at root rather than in a `src/` subpackage. Appropriate for a single-service daemon; avoids import path complexity inside Docker.
- **`web_ui/` subdirectory:** Separate Docker build context and separate `requirements.txt` — correctly isolated from daemon deps.
- **`tests/` flat:** All tests co-located; no subdirectory split needed at current scale (~11 test files).
- **`data/` and `token_cache/`:** Bind-mounted at runtime, excluded from git — should not appear in source tree.

---

## Architectural Patterns

### Pattern 1: File-Based IPC Between Containers

**What:** daemon writes `data/events.jsonl` (append-only) and `data/now_playing.json` (overwrite). web_ui tails events.jsonl for SSE delivery and reads now_playing.json for page-load hydration. Both containers share `./data` via Docker bind-mount volume.

**When to use:** When two containers must share state without a message broker or shared database. Works reliably because both containers run on the same host with `network_mode: host`.

**Trade-offs:** Simple and zero-infrastructure. Tightly coupled to the filesystem. Does not scale across multiple hosts — acceptable for a single-household tool.

### Pattern 2: Shared OAuth Token Volume

**What:** `./token_cache` bind-mount is shared by both containers. The daemon runs `setup_auth.py` once and writes `.cache`. web_ui's spotipy instance reads that same cache — no second OAuth flow needed.

**When to use:** When two services need the same user OAuth token and one service owns auth.

**Trade-offs:** No token rotation isolation. Both services fail if the token expires and the cache is corrupted. Acceptable because the daemon owns the keep-alive polling cycle.

### Pattern 3: Profile Map + ContentChecker Reconstruction

**What:** `PROFILE_MAP` in `daemon.py` defines four named profiles. Scanner objects (`ProfanityScanner`, `DrugScanner`, `SexualContentScanner`) are long-lived singletons. Only the `ContentChecker` wrapper is reconstructed when `active_profile` changes in state.json.

**When to use:** When filter configuration must change at runtime without restarting the service.

**Trade-offs:** Slight indirection — `_build_content_checker()` must be called on profile change, but this is already implemented. Avoids re-initializing heavy word list scanners on every profile change.

---

## Data Flow

### Skip Flow (happy path)

```
Spotify API (poll)
    ↓  track changed
daemon poll_loop()
    ↓  LyricsService.get_lyrics()
    ↓  ContentChecker.check(track)  -- applies active profile rules
    ↓  result.should_skip == True
SocoSkipClient.skip() -- UPnP next()
    ↓  on error 701 (Spotify Connect mode)
SpotifySkipClient.skip() -- Spotify API next()
    ↓
daemon writes events.jsonl (append)
daemon writes now_playing.json (overwrite)
    ↓
web_ui SSE tail -> browser EventSource
```

### FSM Toggle Flow

```
Browser POST /fsm {enabled: true}
    ↓
web_ui _save_state_merge({"family_safe_mode": true})
    ↓
state.json updated on disk
    ↓
daemon poll_loop() reads state.json each cycle (D-06)
    ↓  family_safe_mode == True -> content checking engaged
```

### Profile Change Flow

```
Browser POST /profile {profile: "kids_present"}
    ↓
web_ui _save_state_merge({"active_profile": "kids_present"})
    ↓
daemon poll_loop() detects active_profile change
    ↓
_build_content_checker(profile_key) reconstructs ContentChecker
    ↓  scanner singletons reused; only wrapper rebuilt
```

---

## OSS Release: Hardcoded Personal Details Audit

This is the primary output for the OSS milestone. Every personal detail found in tracked source files is documented here with its risk level and required action.

### Secrets Audit: `.env` File

**Status: SAFE.** The live `.env` file contains real Spotify credentials (`SPOTIFY_CLIENT_ID=886bfa...`, `SPOTIFY_CLIENT_SECRET`) and a real Sonos IP (`SONOS_SPEAKER_IPS=Living Room=192.168.1.164`). However:

- `.env` is in `.gitignore`
- `git log -- .env` returns empty — it was never committed
- `git grep` finds no occurrence of the client ID in any tracked file
- The OAuth token in `./token_cache/` was also never committed

**No action needed for git hygiene.** However, the README and CONTRIBUTING.md should include an explicit reminder that `.env` must never be committed and must not be added to `.gitignore` exceptions.

---

### Priority 1 (Must Fix Before Public Release): Real IP in Tracked Test File

**Files:** `tests/test_sonos_probe.py` (lines 47, 58, 70, 82, 83, 99, 113)

**What's there:** The author's actual home Sonos IP `192.168.1.164` is hardcoded in test fixtures as `mock_speaker.ip_address = "192.168.1.164"` and in assert messages like `"Expected _ip_cache['Living Room'] == '192.168.1.164'"`. This IP appears in git history in `.planning/` docs (in lines that were never production code), but its presence in `tests/test_sonos_probe.py` means it is in the tracked test source.

**Risk:** Moderate. It is a private home network IP used in mocked tests — no real network call is made. But it is personally identifying and visible in the public repo.

**Action:** Replace `192.168.1.164` with `192.168.1.100` throughout `tests/test_sonos_probe.py`. This is a pure text substitution — test behavior is identical because the value is only asserted against itself. Note: `tests/test_skip_client.py` already uses `192.168.1.100` as its example IP — the replacement value matches the existing convention.

---

### Priority 1 (Must Fix Before Public Release): Stale User-Agent String

**File:** `lyrics_service.py`, line 73

**What's there:** `LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")` — uses the pre-rebrand internal codename, not the public app name "Read the Room."

**Action:** Change to `user_agent="ReadTheRoom/1.0"`. This also makes the project's LRCLIB traffic correctly identified.

---

### Priority 1 (Must Fix Before Public Release): Missing `.env.example` Variables

**File:** `.env.example`

**What's missing:** Two variables used by the application are absent from `.env.example`:

1. `UID` and `GID` — used in `docker-compose.yml` as `user: "${UID}:${GID}"`. A stranger who doesn't know to `export UID=$(id -u) GID=$(id -g)` will run containers as root (UID 0), causing bind-mounted files to be root-owned. The README covers this in Quick Start step 4, but `.env.example` should also document it for users who jump straight to `.env`.

2. `EVENTS_PATH` — used in `daemon.py` (`os.environ.get("EVENTS_PATH", "data/events.jsonl")`). The default is sane and works, but the variable is not visible in `.env.example`, making the internal path undiscoverable.

**Recommended additions to `.env.example`:**

```
# Host user IDs — prevents bind-mounted files from being root-owned.
# Run: export UID=$(id -u) GID=$(id -g)
# Or set these explicitly to the output of `id -u` and `id -g`.
# UID=1000
# GID=1000

# Events log path (inside container). Default: data/events.jsonl
# EVENTS_PATH=/app/data/events.jsonl
```

---

### Priority 2 (Fix in Documentation Pass): Module Docstrings with Old Project Name

**Files:** `daemon.py` (line 2), `web_ui/main.py` (line 1), `skip_client.py` (line 2), `content_checker.py` (line 2), `drug_scanner.py` (line 2), `sexual_content_scanner.py` (line 2)

**What's there:** All say "Spotify Family Safe Mode" — the pre-rebrand codename. These appear only via Python's `__doc__` attribute; they are not user-visible in the running application.

**Action:** Update all module docstrings from `"Spotify Family Safe Mode"` to `"Read the Room"` during the documentation pass. Low-urgency but part of a clean OSS release.

---

### Priority 3 (Decision Required): `.planning/` in the Public Repo

**Finding:** `.planning/` is tracked by git — 313 files. It contains:

- Personal household context: `"Music plays through Living Room Sonos (192.168.1.164); Dining Room IP unknown (offline)"` (PROJECT.md line 79)
- Internal development phase history (phase plans, summaries, UAT logs, debug notes)
- Internal milestone decision logs written for the author, not contributors
- Personal notes about children's ages and family context

**Options:**

| Option | Pros | Cons |
|--------|------|------|
| Add `.planning/` to `.gitignore` and remove from tracking | Clean public repo; no personal context leak | Loses project history in the public repo |
| Keep `.planning/` but scrub personal details | Project history preserved | 313 files is noise for contributors; requires individual line edits |
| Keep `.planning/` and add a note in CONTRIBUTING.md that it is internal tooling | No action required | Personal details still visible |

**Recommendation:** Add `.planning/` to `.gitignore` and remove it from tracking (`git rm -r --cached .planning/`). The project history valuable to contributors belongs in CONTRIBUTING.md and the README — not in a directory of AI-assisted development phase logs. This also removes the `192.168.1.164` reference in PROJECT.md without requiring a targeted edit.

---

### Priority 3 (Decision Required): `.claude/` in the Public Repo

**Finding:** `.claude/` is tracked by git — 217 files. It contains the GSD AI-assisted development toolchain: commands, workflows, hooks, templates, and configuration. This is internal development infrastructure with no application logic.

**Risk:** No secrets are present. But 217 files of development tooling visible in the public repo is noise for contributors and implies "you need to set up this AI toolchain to contribute," which is not true.

**Recommendation:** Add `.claude/` to `.gitignore` and remove from tracking. If the GSD toolchain is meant to be public, it belongs in its own dedicated repository, not embedded in this project.

---

### Non-Issues (No Action Required)

| Item | Location | Why No Action Needed |
|------|----------|----------------------|
| `SONOS_SPEAKER_IPS=Dining Room=192.168.1.50,Living Room=192.168.1.51` | `PROXMOX.md` line 29 | Clearly illustrative example IPs in documentation context |
| `# SONOS_SPEAKER_IPS=Dining Room=192.168.1.50,Living Room=192.168.1.51` | `.env.example` line 36 | Commented out, clearly an example |
| `192.168.1.100` in `tests/test_skip_client.py` | Lines 89, 108, 117 | Already a non-personal example IP |
| `user: "${UID}:${GID}"` in `docker-compose.yml` | Line 7, 29 | Correct pattern; documented in README |
| Room names "Living Room", "Dining Room" | Various | Generic room names; not personally identifying |

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Spotify Web API | OAuth via spotipy; scopes: `user-read-playback-state user-read-currently-playing user-modify-playback-state` | Token cached in `./token_cache/.cache` — must not be committed |
| LRCLIB | HTTP via `lrclib` Python package; all failures treated as lyrics-unavailable | No API key required; user_agent string must be updated to `"ReadTheRoom/1.0"` |
| Sonos speakers | SoCo UPnP; SSDP auto-discovery (primary) + `SONOS_SPEAKER_IPS` env var override (escape hatch) | `network_mode: host` required for SSDP multicast |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| daemon to web_ui | File-based IPC via `./data/events.jsonl` and `./data/now_playing.json` | No direct HTTP between containers |
| daemon to web_ui (token) | Shared `./token_cache` bind-mount | Both read same OAuth cache; daemon owns auth |
| daemon to web_ui (state) | Shared `./state.json` bind-mount | web_ui writes; daemon reads each poll cycle |

---

## Anti-Patterns

### Anti-Pattern 1: Publishing `.planning/` Internal Dev Docs to a Public Repo

**What people do:** Leave the entire `.planning/` directory tracked in git when releasing a project. It was created for internal project management and never excluded from `.gitignore`.

**Why it's wrong:** Contains personal household context, private decision rationale written for internal use, and phase/milestone history that reads as noise to a contributor. 313 files inflate repo size and confuse contributors looking at the file tree.

**Do this instead:** Add `.planning/` to `.gitignore` before tagging the public release. Move any contributor-relevant context (project overview, architecture decisions) into CONTRIBUTING.md.

### Anti-Pattern 2: Publishing `.claude/` Internal Tooling to a Public Repo

**What people do:** Track AI development assistant commands, workflows, and hooks in the same repo as the application code.

**Why it's wrong:** 217 files of development tooling provide zero value to contributors who just want to use or contribute to the app. Also implies a toolchain dependency that does not actually exist.

**Do this instead:** Add `.claude/` to `.gitignore`. If the GSD toolchain is meant to be public, it belongs in its own repository.

### Anti-Pattern 3: `UID`/`GID` Without Explicit Documentation

**What people do:** Use `user: "${UID}:${GID}"` in `docker-compose.yml` and assume it works automatically.

**Why it's wrong:** `UID` is a bash read-only variable — it is NOT automatically exported to the environment that `docker compose` reads. On many Linux systems, `docker compose up` with `user: "${UID}:${GID}"` runs as UID 0 silently because the variable is empty. The README covers this correctly, but it is a frequent first-run failure point.

**Do this instead:** The README's Quick Start step 4 is correct. Add a note to CONTRIBUTING.md flagging this as a common first-run failure. Optionally add a `make check-uid` guard that fails early with a clear error if `UID` is unset.

### Anti-Pattern 4: `network_mode: host` Without Explaining Port Access

**What people do:** Use `network_mode: host` for Sonos multicast support but leave contributors confused about dashboard access from remote machines.

**Why it's wrong:** A stranger running on a remote home server expects `http://localhost:8888` but the service is actually reachable at `http://HOST_IP:8888` — with host networking there is no port mapping, just direct exposure.

**Do this instead:** README and CONTRIBUTING.md should explicitly state: "The dashboard is accessible at `http://YOUR_SERVER_IP:8888` from any device on the same network. `network_mode: host` is required for Sonos discovery and cannot be replaced with standard port mapping."

---

## Docker Compose Assessment for a Stranger's Environment

The existing `docker-compose.yml` is correct for a stranger's environment. No structural changes are required.

| Aspect | Status | Notes |
|--------|--------|-------|
| `network_mode: host` | Correct, keep | Required for Sonos SSDP multicast. Cannot replace with port mapping. |
| `env_file: .env` | Correct | All config from `.env`; no interpolation in compose file. |
| `user: "${UID}:${GID}"` | Correct but fragile | Works when `UID`/`GID` are exported. Documented in README. |
| Bind-mount paths (relative `./`) | Correct | Work from any clone location. |
| Shared volumes (`./data`, `./token_cache`, `./state.json`) | Correct | Enable file-based IPC and shared OAuth. |
| Healthcheck | Correct | Touch-file pattern works in any Docker environment. |
| `restart: always` | Correct | Survives host reboots. |

---

## Suggested Execution Order for OSS Changes

Based on dependency analysis:

1. **Sanitize first** — no documentation should reference unsanitized code.
   - Replace `192.168.1.164` with `192.168.1.100` in `tests/test_sonos_probe.py`
   - Update `user_agent="SpotifyFamilySafe/1.0"` to `"ReadTheRoom/1.0"` in `lyrics_service.py`
   - Update module docstrings from "Spotify Family Safe Mode" to "Read the Room" in all 6 Python files
   - Add `UID`/`GID`/`EVENTS_PATH` to `.env.example`
   - Decide on `.planning/` and `.claude/` visibility; add to `.gitignore` if excluding

2. **License and CONTRIBUTING.md** — must exist before promoting the repo.
   - Add `LICENSE` (MIT recommended for a home utility)
   - Write `CONTRIBUTING.md` covering: repo structure, how to run tests, how to submit PRs, the `UID`/`GID` pitfall, `network_mode: host` explanation

3. **CI (GitHub Actions)** — can be added after sanitization; validates the test suite for contributors.
   - Run `pytest tests/` on push/PR
   - Matrix on Python 3.12 minimum

---

## Sources

- Direct inspection of live codebase (`daemon.py`, `lyrics_service.py`, `tests/test_sonos_probe.py`, `tests/test_skip_client.py`, `docker-compose.yml`, `Dockerfile`, `.env`, `.env.example`, `Makefile`, `README.md`, `PROXMOX.md`)
- `git log --all -p` — verified `.env` and `token_cache/` were never committed to history
- `git ls-files` — catalogued all 530+ tracked files including `.planning/` (313) and `.claude/` (217)
- `git grep` — confirmed Spotify client ID is absent from all tracked files

---

*Architecture research for: Read the Room v1.6 — OSS release preparation*
*Researched: 2026-04-06*
