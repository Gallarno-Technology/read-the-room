<!-- CI badges: added in Phase 22 -->

# Read the Room

Read the Room is a self-hosted background service that monitors Spotify playback and automatically skips songs that violate family-safe content rules. It was built to solve a real parenting problem: having young children in the room while music plays. The service runs as a Docker stack on any Linux or macOS machine on your home network, with no cloud dependency and no ongoing subscription.

## Prerequisites

- **A Sonos speaker** configured as a Spotify Connect device. Read the Room skips tracks by sending a UPnP command to the speaker via SoCo (a Python Sonos control library). Spotify Connect mode is required for this to work.

- **Docker and Docker Compose v2.** Verify with `docker compose version` (note: `compose`, not `compose-plugin` — must be v2+).

- **Docker daemon enabled at host boot (Linux):**
  ```bash
  sudo systemctl enable docker
  sudo systemctl is-enabled docker   # should output: enabled
  ```
  Docker Desktop (macOS) starts automatically — no configuration needed.

- **A Spotify developer app** registered at [developer.spotify.com](https://developer.spotify.com/dashboard). You need:
  - Client ID and Client Secret
  - Your redirect URI added to the app's Redirect URIs list — `https://<your-host>/auth/callback`, where `<your-host>` is the LAN IP or domain Caddy serves (e.g. `https://192.168.1.100/auth/callback`)

  Read the Room is single-user: one Spotify account per deployment. (Spotify's development-mode quota caps third-party apps at a handful of listeners, so there is no multi-user mode.)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/read-the-room
   cd read-the-room
   ```

2. **Copy and edit `.env`**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`. The redirect URI must be `https://<your-host>/auth/callback` and must exactly match a Redirect URI registered in your Spotify app dashboard. See `.env.example` for all available options.

3. **Pre-create bind-mount files**
   ```bash
   make setup
   ```
   This creates `state.json`, `token_cache/`, `lyrics_cache.db`, and `data/` so Docker bind mounts have writable targets on the host.

4. **Set UID and GID**
   The containers run as your host user to prevent bind-mounted files from being root-owned. Add these to your `.env`:
   ```
   UID=<output of `id -u`>
   GID=<output of `id -g`>
   ```
   Or export them in your shell before running any compose commands:
   ```bash
   export UID=$(id -u) GID=$(id -g)
   ```

5. **Start the service**
   ```bash
   docker compose up -d
   ```

6. **Authenticate with Spotify (one time)**
   Open the dashboard in a browser. On first visit — before any token exists — it redirects you to Spotify's authorization page. Approve access, and the `/auth/callback` route writes the token to `token_cache/.cache`, which the `daemon` container picks up on its next poll. No CLI step is required.

7. **Open the dashboard** — `https://<your-host>` (Caddy) or `http://localhost:8888` (web_ui directly)

## How It Works

The `daemon` container polls the Spotify playback API on an adaptive cadence (faster while a track is playing, slower when idle) to see what is currently playing. When a new track starts, it checks the Spotify explicit flag first. If the track is flagged explicit, it is skipped immediately — no lyrics fetch needed.

If the explicit flag is not set, the daemon fetches lyrics from LRCLIB, a public and free lyrics API. The lyrics are rated by an LLM (Claude by default, behind a pluggable provider interface) and the active filter profile decides whether the rating passes. Lyric scan results are cached in a local SQLite database so the same track is not fetched twice.

When a track fails the content check, Read the Room sends a skip command to the Sonos speaker via SoCo using UPnP. If the speaker is unreachable or returns an error (for example, when Sonos is in Spotify Connect mode), the daemon falls back to the Spotify API skip command. A Docker healthcheck confirms the daemon is alive by checking a `.healthcheck` file that the daemon touches every polling cycle. The dashboard, served by FastAPI on port 8888, shows the current track, a Family Safe Mode toggle, skip history, and a filter profile selector.

## Filter Profiles

Read the Room ships with three named profiles. Each song is rated once by an LLM against a profile-agnostic rubric (sexual content, drug references, violence, dark themes, language, and overall framing) and the result is cached. The active profile's verdict is then derived from that cached rating in code, so switching profiles from the dashboard is instant and never re-evaluates a song. The rating covers themes the keyword scanners cannot see, such as violence on clean lyrics or a cautionary versus glorifying take on drugs. Tracks Spotify flags explicit are still skipped under every profile except where noted, and a track the model cannot rate confidently is skipped and routed to manual review.

### Family Friendly

The strictest profile and the default. It skips any song with innuendo or stronger sexual content, casual or heavier drug references, narrative or graphic violence, present or prominent dark themes, moderate or heavy language, or an objectifying, glorifying or transactional framing. Use it when young children are in the room.

### Mixed Company

For a mixed crowd. It skips explicit sexual content, hard-drug references that are not cautionary, graphic violence, prominent dark themes, heavy language, and objectifying, glorifying or transactional framing. Heavy language used in a cultural register (for example in an artistic context) is not treated as a slur.

### Close Friends

The lightest touch: "we're not a censor." It skips only explicit sexual content and slurs used as slurs. Everything else passes.

See `profiles.py` for the exact decision rules and `.env.example` for the LLM settings (`ANTHROPIC_API_KEY`, `SENTIMENT_MODEL`). If the LLM tier is disabled or has no API key, the daemon falls back to the keyword-only pipeline (profanity, drug and sexual-content scanners plus the explicit flag).

## Sonos Notes

Read the Room uses SSDP (multicast) to discover Sonos speakers automatically on startup. No configuration is needed if your speakers are on the same network segment as the host running Docker.

If SSDP discovery fails — due to a firewall, VLAN, or virtualized host — set `SONOS_SPEAKER_IPS` in your `.env`:
```
SONOS_SPEAKER_IPS=Living Room=192.168.1.50
```
Use the exact room name that Spotify reports for the device.

Proxmox/LXC users: Sonos SSDP requires multicast bridge forwarding. See [PROXMOX.md](PROXMOX.md).

## Updating

```bash
git pull && docker compose up -d --build
```

Data files (`state.json`, `lyrics_cache.db`, `token_cache/`, `data/`) are bind-mounted on the host and survive rebuilds — no manual migration needed.

## License

This repository is proprietary software. See [LICENSE](LICENSE) for the full terms.

A hosted cloud version is planned as a separate service developed in its own repository.
