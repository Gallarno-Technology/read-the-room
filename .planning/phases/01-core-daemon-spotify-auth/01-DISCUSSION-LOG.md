# Phase 1: Core Daemon & Spotify Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 01-core-daemon-spotify-auth
**Areas discussed:** Auth setup UX, Logging & observability, Idle polling behavior, Deployment (LaunchAgent → Docker)

---

## Auth Setup UX

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-open browser | webbrowser.open() + local callback server | |
| Print URL, user pastes code | Print auth URL, prompt for redirect URL paste-back | ✓ |
| Auto-open with fallback | Try auto-open, fall back to print | |

**User's choice:** Print URL to terminal — user will be SSH'd from a mobile device and cannot interact with a browser on the host machine.

**Post-auth behavior:**

| Option | Description | Selected |
|--------|-------------|----------|
| Print confirmation and exit | Simple success message | |
| Auto-start daemon | Launch daemon.py immediately after auth | |
| Run a quick validation | Test API call to confirm token, then print success | ✓ |

**Notes:** The constraint that drove this decision: user accesses the host via SSH from a mobile device on the local network. Auto-open browser would open on the server (no display), not on the user's device.

---

## Logging & Observability

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text with timestamps | Human-readable, easy to tail over SSH | ✓ |
| Structured JSON | Machine-parseable | |
| Plain text, no timestamps | Simplest | |

**Log destination:**

| Option | Description | Selected |
|--------|-------------|----------|
| ~/Library/Logs/spotify-sentinel/ | macOS standard | (superseded) |
| stdout (Docker) | Docker captures stdout; docker logs for viewing | ✓ |

**Notes:** Log destination was initially discussed as ~/Library/Logs but was superseded when deployment target clarified as Docker on Proxmox. stdout is the Docker-idiomatic choice.

**Log rotation:**

| Option | Description | Selected |
|--------|-------------|----------|
| Python RotatingFileHandler | Built-in rotation | (superseded) |
| Docker logging driver | docker-compose handles rotation | ✓ |
| No rotation | Simplest | |

**Notes:** RotatingFileHandler was the initial pick but superseded by Docker deployment decision. Docker's logging driver handles rotation.

---

## Idle Polling Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Back off to 5s when idle | Adaptive rate — 1s playing, 5s idle | |
| Always poll at 1s | Fixed rate, configurable via .env | ✓ |
| Stop polling until resumed | Lowest API usage, needs wake mechanism | |

**User's choice:** Fixed 1s always. Configurable via `.env`.

**Clarification exchange:** User asked "what's polling used for?" — clarified that Spotify has no push events/webhooks; polling `GET /me/player/currently-playing` is the only way to detect track changes. User understood the tradeoff and chose simplicity (fixed rate) over optimization (adaptive).

**Idle logging:**

| Option | Description | Selected |
|--------|-------------|----------|
| Silent when idle | Log nothing when no playback | |
| Periodic heartbeat | Log alive message every N minutes | ✓ |
| Every poll cycle | Very verbose, debug only | |

---

## LaunchAgent Installation → Docker Deployment

**Original questions were about macOS LaunchAgent installation. User clarified:**
- Development machine: Arch Linux
- Production: Proxmox
- macOS LaunchAgent is not applicable

| Option | Description | Selected |
|--------|-------------|----------|
| Docker + docker-compose | Daemon + signal-cli-rest-api in same stack | ✓ |
| LXC on Proxmox | Lighter, more Proxmox-native | |
| Bare metal systemd service | Direct systemd on Proxmox | |

**User's choice:** Docker.

**Key implications locked:**
- `network_mode: host` required for SoCo UPnP/multicast
- `restart: always` for auto-restart on crash
- `.env` file as config source
- CORE-03 in REQUIREMENTS.md needs updating (macOS LaunchAgent → Docker service)

---

## Claude's Discretion

- Exact 429 backoff algorithm
- Heartbeat interval and log message wording
- `.env` variable naming
- `state.json` schema for Phase 1 (current track ID persistence)

## Deferred Ideas

- Adaptive polling rate (user chose fixed 1s)
- Sonos auto-detection of Family Safe Mode (v2)
