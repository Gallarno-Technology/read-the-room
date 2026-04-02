# Phase 5: Deployment & Documentation - Research

**Researched:** 2026-04-02
**Domain:** Docker Compose healthchecks, README authoring, boot persistence, documentation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Target reader is "me, returning after weeks away" — assume Docker familiarity and project-level amnesia. Optimize for re-setup speed over first-timer hand-holding.
- **D-02:** Quick-start block first (top of README), then detail sections below. Structure: Quick Start → Prerequisites → Updating. Skimmable.
- **D-03:** Quick-start uses explicit docker commands (not Makefile targets). Raw `docker compose run --rm -it daemon python setup_auth.py` and `docker compose up -d` — no Makefile dependency. The existing Makefile targets remain available but are not the canonical flow in the README.
- **D-04:** README sections below quick-start: Prerequisites (Docker, docker compose, Spotify app registration, UID:GID) and Updating (`git pull && docker compose up -d --build`). No troubleshooting section, no configuration reference (`.env.example` is self-documenting).
- **D-05:** Sonos setup is NOT a separate README section. Proxmox/LXC multicast notes go in a separate `PROXMOX.md` file, linked from the quick-start or prerequisites where relevant.
- **D-06:** High-level note only — no specific nftables commands or bridge config steps. "Proxmox LXC containers require multicast bridge forwarding to be enabled for Sonos SSDP discovery. See your Proxmox documentation or `PROXMOX.md` for guidance." Points reader in the right direction without risking outdated or environment-specific commands.
- **D-07:** Proxmox notes live in `PROXMOX.md` (repo root), linked from README where Sonos is mentioned. Content: what multicast forwarding is, why it's needed for SSDP, high-level note about enabling it in Proxmox, and the `SONOS_SPEAKER_IPS` fallback as an alternative if bridge config isn't possible.
- **D-08:** Add a Docker healthcheck to `docker-compose.yml` for the daemon service. Check whether the daemon Python process is alive and recently active. Recommended approach: `test: ["CMD", "python", "-c", "import os, time; f='.healthcheck'; assert time.time()-os.stat(f).st_mtime<60"]` where the daemon touches a `.healthcheck` file each poll cycle. Interval 30s, timeout 10s, retries 3, start_period 15s. On failure: Docker restarts the container automatically (relies on `restart: always`).
- **D-09:** Apply healthcheck to `daemon` service only — `web_ui` service does not need one for v1.
- **D-10:** Update procedure is: `git pull && docker compose up -d --build`. Document in README's Updating section. No `make update` target needed. State explicitly that bind-mounted data files (`state.json`, `lyrics_cache.db`, `token_cache/`, `data/`) are on the host and survive rebuilds.
- **D-11:** No migration tooling in Phase 5. The bind-mount pattern means no data is inside containers — rebuilding the image is safe. If a future phase adds a new bind-mount file, `make setup` is the right place to pre-create it.

### Claude's Discretion

- Exact wording and formatting of README sections
- Healthcheck file path and daemon-side touch implementation (can be in `poll_loop()` or a wrapper)
- Whether to add a `healthcheck` to `web_ui/Dockerfile` as well (recommended: no — start simple)
- PROXMOX.md depth and format

### Deferred Ideas (OUT OF SCOPE)

- Troubleshooting section in README
- Configuration reference section
- Healthcheck for web_ui service
- `make update` target
- Specific nftables/bridge commands for Proxmox

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPL-01 | README covers complete first-time setup: prerequisites, clone, `.env` config, Spotify OAuth, and `docker compose up -d` | README structure decisions D-01 through D-04 captured; see Architecture Patterns |
| DEPL-02 | README documents Sonos network requirements (multicast UDP port 1900, firewall rules, Proxmox LXC bridge config) | D-05 through D-07 define PROXMOX.md split; see Common Pitfalls §Multicast |
| DEPL-03 | Service survives host reboots without manual intervention — Docker daemon auto-start documented and verified | `restart: always` already in docker-compose.yml; Docker daemon autostart is OS-level; see Boot Persistence |
| DEPL-04 | `docker-compose.yml` includes a healthcheck that detects a silently hung daemon and triggers automatic restart | D-08/D-09 specify exact healthcheck YAML; see Architecture Patterns §Healthcheck |
| DEPL-05 | Updating to a new version requires only `git pull && docker compose up -d --build` — no manual migration steps, data safe | Bind-mount pattern already guarantees this; D-10/D-11 confirm; see Update Workflow |

</phase_requirements>

---

## Summary

Phase 5 is a documentation and configuration phase — no new Python features, no new env vars. Three deliverables: `README.md` (new file), `PROXMOX.md` (new file), and a healthcheck block added to `docker-compose.yml`'s `daemon` service. One line of Python (`Path('.healthcheck').touch()`) is added inside `poll_loop()`.

All user decisions are fully locked. The healthcheck mechanism (touch-file probe) is idiomatic for long-running poll loops where a process can be alive but silently deadlocked. The bind-mount architecture already makes `git pull && docker compose up -d --build` safe — Phase 5 just documents that fact.

Boot persistence (`restart: always`) is already in `docker-compose.yml`. The only gap is that the Docker daemon itself must be enabled at boot on the host OS. This is `systemctl enable docker` on Linux (systemd) or auto-start on Docker Desktop — document as a prerequisite, not a runtime concern.

**Primary recommendation:** Three focused tasks: (1) add healthcheck to docker-compose.yml + touch in daemon.py, (2) write README.md, (3) write PROXMOX.md.

---

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| Docker Compose | v2 (compose v5.1.1 installed) | Service orchestration | Already in use |
| Python 3.12 | (container) | Healthcheck probe language | Already in Dockerfile |
| pytest-asyncio | latest | Async test support | Already used in test suite |

### Supporting

| Tool | Purpose | When to Use |
|---|---|---|
| `pathlib.Path.touch()` | Update `.healthcheck` file mtime | Per poll_loop() iteration |
| Docker `HEALTHCHECK` directive | Alternative location (Dockerfile) | Prefer compose over Dockerfile for this project — config stays in one place |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Touch-file mtime probe | HTTP probe against an internal endpoint | Touch-file is simpler; no HTTP server needed in daemon container |
| Touch-file mtime probe | `pgrep daemon.py` process check | Process-alive check misses silent hangs (deadlocked event loop); mtime proves liveness |
| compose `healthcheck` block | `HEALTHCHECK` in `Dockerfile` | Dockerfile healthcheck is harder to override per-environment; compose is the right layer here |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended File Layout

```
(repo root)
├── README.md          # NEW — Quick Start → Prerequisites → Updating
├── PROXMOX.md         # NEW — multicast context + SONOS_SPEAKER_IPS escape hatch
├── docker-compose.yml # MODIFY — add healthcheck block to daemon service
└── daemon.py          # MODIFY — add Path('.healthcheck').touch() in poll_loop()
```

### Pattern 1: Docker Compose Healthcheck (Touch-File Probe)

**What:** Daemon writes `.healthcheck` to the container working directory (`/app`) on every poll cycle. The healthcheck CMD checks that the file was modified within the last 60 seconds. If the file goes stale (daemon hung), Docker marks the container unhealthy and `restart: always` triggers a restart.

**When to use:** Long-running async loops where a deadlocked event loop keeps the process alive but stops doing work.

**docker-compose.yml addition (daemon service):**
```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import os, time; f='.healthcheck'; assert time.time()-os.stat(f).st_mtime<60"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

**daemon.py addition (inside `poll_loop()` while loop, top of each iteration):**
```python
from pathlib import Path

# Inside poll_loop(), at the top of `while not stop_event.is_set():`
Path('.healthcheck').touch()
```

**Why `start_period: 15s`:** The daemon startup includes an SSDP probe with a 5-second timeout (`soco.discovery.discover` default). `start_period` gives the container time to complete startup before the first health evaluation — avoids false-unhealthy on initial boot.

**Why retries=3:** Three consecutive failures (at 30s each) = 90 seconds of confirmed hang before restart. Avoids restarting on transient slowness.

**Confidence:** HIGH — derived directly from D-08 in CONTEXT.md and verified against Docker Compose healthcheck documentation.

### Pattern 2: README Structure

**Target:** "Me, returning after weeks away" — Docker-familiar, project-amnesiac.

```markdown
# Spotify Family Safe Mode

One-line description.

## Quick Start

1. Clone and copy env: `git clone ... && cp .env.example .env`
2. Edit `.env` (Spotify credentials)
3. Pre-create bind-mount files:
   `echo '{"last_track_id": null}' > state.json && mkdir -p token_cache data && touch lyrics_cache.db`
4. One-time OAuth: `docker compose run --rm -it daemon python setup_auth.py`
5. Start: `docker compose up -d`
6. Dashboard: http://localhost:8888

## Prerequisites

- Docker + docker compose (v2)
- Docker daemon enabled at host boot (`systemctl enable docker`)
- Spotify app registered at developer.spotify.com (Client ID, Secret, Redirect URI)
- Host UID:GID set in shell: `export UID GID` or hardcode in `.env`
- [Proxmox/LXC users: see PROXMOX.md]

## Updating

git pull && docker compose up -d --build

Data files (state.json, lyrics_cache.db, token_cache/, data/) are bind-mounted
on the host and survive rebuilds — no manual migration needed.
```

**Bind-mount pre-creation note:** The Makefile `setup` target does this. README quick-start inlines the raw commands per D-03.

### Pattern 3: PROXMOX.md Structure

```markdown
# Proxmox / LXC Multicast Notes

Why Sonos SSDP discovery may fail in LXC containers, and how to fix it.

## Why This Matters

SSDP discovery uses UDP multicast on port 1900. Proxmox LXC containers
run on a Linux bridge (vmbr0 by default). By default, multicast traffic
is not forwarded across that bridge into LXC network namespaces.

## Fix

Enable multicast bridge forwarding on the Proxmox host. See:
https://pve.proxmox.com/wiki/Network_Configuration

## Escape Hatch

If bridge config isn't possible, set SONOS_SPEAKER_IPS in .env:
  SONOS_SPEAKER_IPS=Dining Room=192.168.1.50,Living Room=192.168.1.51
Find IPs: Sonos app → Settings → System → [Room] → About [Room]
```

### Anti-Patterns to Avoid

- **Dockerfile HEALTHCHECK instead of compose healthcheck:** Puts operational config in a build artifact. Harder to adjust without rebuilding. Compose is the right layer.
- **Process-only liveness check (`pgrep`):** Misses event-loop deadlocks. Mtime probe is strictly better for async workloads.
- **Including specific firewall commands in PROXMOX.md:** D-06 explicitly forbids this — commands vary by Proxmox version and bridge config. Point to official docs.
- **Duplicate `.env` documentation in README:** `.env.example` is self-documenting. README says "copy and edit" and stops there (D-04).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Container restart on hang | Custom watchdog script | `restart: always` + healthcheck | Docker handles this natively; custom watchdog adds complexity |
| Boot persistence | systemd unit for the app | `restart: always` + `systemctl enable docker` | Docker daemon at boot + restart policy is the standard pattern |
| Data migration | Custom migrate.py | Bind-mount pattern | All data is on host already — no migration needed |

**Key insight:** The bind-mount architecture (established in Phase 1) is the reason DEPL-05 is already satisfied by design. Phase 5 documents what's already true, then adds the one missing piece (healthcheck).

---

## Boot Persistence — What's Already True vs. What Needs Documentation

### Already in docker-compose.yml
- `restart: always` on both `daemon` and `web_ui` services

### What `restart: always` covers
- Container crash → automatic restart
- Container hung → automatic restart (once healthcheck triggers)
- `docker compose up -d` after `docker compose down` → requires manual up

### What `restart: always` does NOT cover
- The Docker daemon itself must be enabled at host boot. If Docker doesn't start, no containers start.

### Linux (systemd) — document as prerequisite
```bash
sudo systemctl enable docker
sudo systemctl is-enabled docker   # Verify: should output "enabled"
```

### Docker Desktop (macOS/Windows)
Docker Desktop starts automatically by default. No action needed — document as "Docker Desktop auto-starts; no configuration needed."

### Verification command (for README or DEPL-03 test)
```bash
# After reboot, verify services came up:
docker compose ps
```

**Confidence:** HIGH — behavior of `restart: always` with Docker daemon autostart is well-documented and matches STATE.md note: "docker restart:always already in docker-compose.yml — Phase 5 just needs to document and verify this."

---

## Common Pitfalls

### Pitfall 1: Healthcheck File Path Confusion

**What goes wrong:** `.healthcheck` written at `/app/.healthcheck` (container WORKDIR) but healthcheck CMD uses a relative path that resolves differently depending on where Python is invoked. Both the touch and the stat must use the same path.

**Why it happens:** The CMD in `test` runs a new Python process; its cwd is `/app` (WORKDIR). The daemon also runs in `/app`. Relative paths agree. No issue in practice — but explicit is better.

**How to avoid:** Use `Path('/app/.healthcheck').touch()` (absolute path) in daemon.py to be explicit. Match in CMD: `f='/app/.healthcheck'`.

**Warning signs:** Healthcheck reports "no such file or directory" in `docker inspect` output.

### Pitfall 2: start_period Too Short

**What goes wrong:** Container is marked unhealthy before the daemon finishes SSDP discovery startup (5-second probe). Docker restarts it. Restart loop on first boot.

**Why it happens:** Default `start_period: 0s`. SSDP probe takes up to 5s. If healthcheck fires at 0s and file hasn't been touched yet, container is immediately unhealthy.

**How to avoid:** `start_period: 15s` as specified in D-08. Gives daemon ~10s of margin past the 5s SSDP timeout.

**Warning signs:** Container enters restart loop immediately after first start; logs show probe_sonos_speakers completing then container dying.

### Pitfall 3: UID:GID Not Set Before docker compose up

**What goes wrong:** `user: "${UID}:${GID}"` in compose resolves to `user: ":"` if `UID` and `GID` are not exported in the calling shell. Container runs as an unexpected UID; bind-mount writes may fail or create root-owned files.

**Why it happens:** `UID` is a bash read-only variable but may not be exported. `GID` is usually not set at all.

**How to avoid:** README Prerequisites must instruct the user to either:
  - Add `export UID=$(id -u) GID=$(id -g)` to their shell profile, OR
  - Set `UID` and `GID` directly in `.env`

**Warning signs:** `docker compose up` produces permission errors on bind-mount files; `docker compose config` shows `user: ":"`.

### Pitfall 4: Bind-Mount Files Not Pre-Created

**What goes wrong:** Docker creates the bind-mount targets as directories if they don't exist as files. `state.json` becomes a directory; daemon fails to write JSON.

**Why it happens:** `docker compose up` auto-creates missing bind-mount paths as directories.

**How to avoid:** README Quick Start step 3 must include the pre-creation commands. `make setup` does this; README inlines the raw commands (D-03).

**Warning signs:** `docker compose logs daemon` shows `IsADirectoryError: [Errno 21] Is a directory: 'state.json'`.

### Pitfall 5: Multicast UDP 1900 Blocked by Host Firewall

**What goes wrong:** SSDP discovery returns no speakers even on a properly bridged network. Daemon logs actionable warning but user doesn't see firewall as the cause.

**Why it happens:** Common Linux firewall defaults (ufw, iptables) block incoming UDP. `network_mode: host` means the daemon uses the host's network stack, so host firewall rules apply.

**How to avoid:** README Prerequisites or PROXMOX.md should note: "If SSDP discovery fails, check host firewall allows UDP port 1900 (multicast)." The daemon already logs this hint (Phase 4, DISC-03).

**Warning signs:** `[SONOS] No speakers found via SSDP` in daemon logs immediately after start.

---

## Code Examples

### Healthcheck CMD (verified against Docker Compose schema)

```yaml
# docker-compose.yml — daemon service
healthcheck:
  test: ["CMD", "python", "-c", "import os, time; f='/app/.healthcheck'; assert time.time()-os.stat(f).st_mtime<60"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

### daemon.py poll_loop() touch (top of while loop)

```python
from pathlib import Path

# Inside poll_loop(), while not stop_event.is_set():
Path('/app/.healthcheck').touch()
# ... rest of loop body
```

### Linux Docker daemon autostart verification

```bash
sudo systemctl enable docker
sudo systemctl is-enabled docker  # Expected output: "enabled"
```

### Check healthcheck status after start

```bash
docker inspect $(docker compose ps -q daemon) | python3 -m json.tool | grep -A5 Health
# Or:
docker compose ps  # Shows (healthy) / (unhealthy) status
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Docker | All DEPL requirements | Yes | 29.3.1 | — |
| Docker Compose v2 | All DEPL requirements | Yes | 5.1.1 | — |
| Python 3 (host) | Healthcheck test command (inside container) | Yes (container) | 3.12 (container) | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

**Note:** pytest is not installed on the host Python (3.14.3). Tests run inside the container via `docker compose run --rm daemon python -m pytest tests/` or require `pip install pytest pytest-asyncio` in the host/venv. The existing test suite was presumably run via container or venv. No new test infrastructure needed for Phase 5 (see Validation Architecture).

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest + pytest-asyncio |
| Config file | None found — no pytest.ini / pyproject.toml |
| Quick run command | `docker compose run --rm daemon python -m pytest tests/ -x -q` |
| Full suite command | `docker compose run --rm daemon python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| DEPL-01 | README covers complete first-time setup | manual | — read through README | ❌ n/a (doc) |
| DEPL-02 | README documents Sonos network requirements + PROXMOX.md exists | manual | — verify PROXMOX.md exists and is linked | ❌ n/a (doc) |
| DEPL-03 | Service survives reboot | manual | `docker compose ps` after simulated restart | ❌ n/a (host-level) |
| DEPL-04 | Healthcheck detects hung daemon and triggers restart | unit | `pytest tests/test_healthcheck.py -x` | ❌ Wave 0 |
| DEPL-05 | `git pull && docker compose up -d --build` is safe | manual | verify bind-mounts survive rebuild | ❌ n/a (operational) |

### DEPL-04 Unit Test Approach

The healthcheck is a file-mtime contract. Two unit tests cover it:

1. **`test_poll_loop_touches_healthcheck_file`** — mock the Spotify client, run one poll cycle, assert `/app/.healthcheck` (or a tmp path) was created/touched.
2. **`test_healthcheck_cmd_detects_stale_file`** — unit test the CMD logic: given a file with mtime > 60s ago, assert the assertion fails; given fresh mtime, assert it passes.

Tests go in `tests/test_healthcheck.py`.

### Sampling Rate

- **Per task commit:** `docker compose run --rm daemon python -m pytest tests/test_healthcheck.py -x -q`
- **Per wave merge:** `docker compose run --rm daemon python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_healthcheck.py` — covers DEPL-04 (healthcheck touch behavior)

*(All other phase requirements are documentation/operational — no automated tests feasible)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `docker-compose` (v1, hyphen) | `docker compose` (v2, plugin) | Docker 20.10+ | Use `docker compose` in all README commands — v1 is deprecated |
| `restart: on-failure` | `restart: always` | — | `always` restarts on any exit, including clean exits; combined with healthcheck, this is the standard for daemons |
| `HEALTHCHECK` in Dockerfile | `healthcheck:` in compose | Compose v2 | Compose-level healthcheck is environment-specific config, not build config |

**Deprecated/outdated:**
- `docker-compose` (with hyphen, v1): EOL. All README examples must use `docker compose` (v2 syntax). This project already uses v2 in the Makefile.

---

## Open Questions

1. **Absolute vs. relative path for `.healthcheck` file**
   - What we know: WORKDIR is `/app`; both daemon and healthcheck CMD run from `/app`
   - What's unclear: Whether relative path `.healthcheck` is reliable across all Docker versions
   - Recommendation: Use absolute `/app/.healthcheck` in both daemon.py and the CMD to be unambiguous

2. **UID:GID in .env vs. shell export**
   - What we know: compose uses `${UID}:${GID}`; README must address this
   - What's unclear: Whether to recommend shell profile export or `.env` entry
   - Recommendation: README should show both options; `.env` entry is more portable across CI and SSH sessions

3. **Does the healthcheck file need to be in a bind-mount volume?**
   - What we know: `.healthcheck` is inside the container at `/app/.healthcheck`; it is not bind-mounted
   - What's unclear: Whether loss of the file on container restart causes a bootstrap problem
   - Recommendation: No — the healthcheck only needs to exist after the daemon has started its first poll cycle; `start_period: 15s` covers the window before first touch

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `docker-compose.yml`, `daemon.py`, `Makefile`, `.env.example`, `Dockerfile` — current state of existing infrastructure
- CONTEXT.md D-08: exact healthcheck YAML specified by user discussion
- Docker Compose documentation (healthcheck schema): `interval`, `timeout`, `retries`, `start_period` fields — standard reference

### Secondary (MEDIUM confidence)

- STATE.md note: "docker restart:always already in docker-compose.yml — Phase 5 just needs to document and verify this"
- Docker `restart: always` behavior with `systemctl enable docker` — standard Linux Docker deployment pattern

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in use; no new dependencies
- Architecture: HIGH — decisions fully locked in CONTEXT.md; healthcheck pattern is standard Docker
- Pitfalls: HIGH — derived from code inspection of actual bind-mount setup and existing WORKDIR/UID patterns
- Boot persistence: HIGH — `restart: always` already present; Linux systemd pattern is standard

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable Docker Compose API; no fast-moving dependencies)
