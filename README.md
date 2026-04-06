# Read the Room

Automatically skips explicit songs when Read the Room is on. Polls Spotify playback, checks lyrics, and skips via Sonos or the Spotify API.

## Quick Start

1. **Clone and copy env**

   ```bash
   git clone <repo-url>
   cd spotify-sentiment
   cp .env.example .env
   ```

2. **Edit `.env`**

   Fill in `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`. See the comments in `.env.example` for details.

3. **Pre-create bind-mount files**

   ```bash
   echo '{"last_track_id": null}' > state.json && mkdir -p token_cache data && touch lyrics_cache.db
   ```

   (Or run `make setup` if you have Make installed.)

4. **Set UID and GID**

   The containers run as your host user — this prevents bind-mounted files from being root-owned. Export before running any compose commands:

   ```bash
   export UID=$(id -u) GID=$(id -g)
   ```

   Or add `UID` and `GID` directly to your `.env` file:

   ```
   UID=<your-uid>
   GID=<your-gid>
   ```

5. **One-time Spotify OAuth**

   ```bash
   docker compose run --rm -it daemon python setup_auth.py
   ```

   A browser window opens. Approve access in Spotify, then the browser will fail to load the redirect page — this is expected. Copy the full URL from the address bar and paste it back into the terminal.

6. **Start the service**

   ```bash
   docker compose up -d
   ```

7. **Dashboard** — [http://localhost:8888](http://localhost:8888)

> **Proxmox/LXC users:** Sonos SSDP discovery requires multicast bridge forwarding. See [PROXMOX.md](PROXMOX.md).

## Prerequisites

- **Docker + docker compose (v2)** — run `docker compose version` to confirm v2+.
- **Docker daemon enabled at host boot (Linux):**

  ```bash
  sudo systemctl enable docker
  sudo systemctl is-enabled docker   # should output: enabled
  ```

  Docker Desktop (macOS/Windows) auto-starts — no configuration needed.

- **Spotify app registered** at [developer.spotify.com](https://developer.spotify.com/dashboard) — you need Client ID, Client Secret, and a Redirect URI (`https://127.0.0.1:8080`) added to the app's Redirect URIs list.

- **UID and GID set** in your shell or `.env` (see Quick Start step 4).

## Updating

```bash
git pull && docker compose up -d --build
```

Data files (`state.json`, `lyrics_cache.db`, `token_cache/`, `data/`) are bind-mounted on the host and survive rebuilds — no manual migration needed.
