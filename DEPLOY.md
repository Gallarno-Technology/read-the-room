# Prod deployment — Read the Room

Single-household, self-hosted. No CI/CD — deploys are manual file pushes into an
LXC container, not a git pull.

Addresses below are intentionally omitted (this repo is public) — this
assumes you're already on the right Tailscale tailnet; run `tailscale status`
to resolve the node names mentioned here to their current IP/MagicDNS name.

## Topology

- **Proxmox host:** Tailscale node `pve`. SSH as `root` works with the
  default key, no password, no `~/.ssh/config` entry needed — connect by
  Tailscale IP (resolve via `tailscale status`).
- **App container:** LXC container running inside `pve`, Tailscale node
  `read-the-room`. Debian, runs its own `tailscaled`.
  - There is **no working SSH access directly into the container** — no known
    user/key is authorized on it. All access goes through the Proxmox host
    via `pct exec <vmid> -- <cmd>` (get the vmid from `pct list` on `pve`).
  - `/opt/read-the-room` on the container is **not a git repo** — it's a plain
    copy of this repo's files. `git pull`-based deploys won't work; files must
    be pushed in individually (see below).
- **App stack:** `docker compose` inside the container, three services defined
  in `docker-compose.yml`:
  - `daemon` — the Spotify poll loop (`daemon.py`).
  - `web_ui` — FastAPI/uvicorn on `:8888`, reads `web_ui/templates/index.html`
    fresh from disk on every request (no template caching, no build step).
  - `caddy` — reverse proxy, terminates HTTPS on `:443` (host networking).
    Gets a **real Let's Encrypt cert** for the container's Tailscale MagicDNS
    name via Caddy's built-in Tailscale cert manager — no self-signed
    warnings. Requires the host's Tailscale socket bind-mounted in (see
    `docker-compose.yml`): `/var/run/tailscale/tailscaled.sock`.

## Reaching the app

- **UI:** `https://read-the-room.<your-tailnet>.ts.net/` — works from any
  device on the tailnet (phone, desktop), trusted cert, no warnings.
- **Reauth Spotify:** same host + `/auth/login` (also linked from the UI's
  idle state: "Expecting to see something here? Reauth"). Registered
  redirect URI in the Spotify Developer Dashboard must exactly match
  `SPOTIFY_REDIRECT_URI` in the container's `.env`.

## Running commands against prod

Everything goes through the Proxmox host, then `pct exec`:

```bash
# one-off command inside the container
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- <command>"

# compose commands need the cwd set
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- bash -lc 'cd /opt/read-the-room && docker compose <args>'"
```

Useful ones:

```bash
docker compose ps                       # container status
docker compose logs --tail=50 daemon    # daemon logs (watch for SpotifyOauthError)
docker compose logs --tail=50 web_ui
docker compose logs --tail=50 caddy
docker compose up -d <service>          # recreate one service (picks up new .env)
```

Avoid `cat`-ing `.env` wholesale over SSH — it holds the Spotify client
secret and (if configured) an Anthropic key. Use `grep` for a specific key
instead, e.g. `grep -i poll_interval .env`.

## Deploying a code change

There's no build pipeline — pick the lightest option that applies:

**Template-only change** (`web_ui/templates/index.html`) — hot-swappable,
no restart, since `web_ui` reads it from disk per-request:

```bash
scp web_ui/templates/index.html root@<pve-tailscale-ip>:/tmp/index.html
ssh root@<pve-tailscale-ip> "pct push <vmid> /tmp/index.html /opt/read-the-room/web_ui/templates/index.html"
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- docker cp /opt/read-the-room/web_ui/templates/index.html read-the-room-web_ui-1:/app/web_ui/templates/index.html"
ssh root@<pve-tailscale-ip> "rm -f /tmp/index.html"
```

**Python code change** (`daemon.py`, `web_ui/main.py`, etc.) — the
Dockerfiles `COPY . .` at build time, so these need an image rebuild, not
just a file copy. Push every changed file the same way as above with
`pct push`, then:

```bash
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- bash -lc 'cd /opt/read-the-room && docker compose up -d --build <service>'"
```

**`docker-compose.yml` / `Caddyfile` change** — push the file with `pct push`
the same way, then `docker compose up -d <service>` to apply it (add
`--build` too if a Dockerfile also changed).

**`.env` change** (e.g. `POLL_INTERVAL_ACTIVE`/`IDLE`) — edit in place with
`sed` via `pct exec` (don't round-trip the whole file through chat), then
recreate the service that reads it:

```bash
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- sed -i 's/^POLL_INTERVAL_ACTIVE=.*/POLL_INTERVAL_ACTIVE=2/' /opt/read-the-room/.env"
ssh root@<pve-tailscale-ip> "pct exec <vmid> -- bash -lc 'cd /opt/read-the-room && docker compose up -d daemon'"
```

⚠️ Current prod values: `POLL_INTERVAL_ACTIVE=2`, `POLL_INTERVAL_IDLE=10`
(bumped from the 5s/30s defaults for faster single-user catch, 2026-10-03).
Spotify's rate limit is per-app, not per-user, and tight polling caused a
~9.7h lockout once before (see `.env.example` comments) — don't go below
these without reason.

**Whichever path you used, also update the matching file in this repo** —
`/opt/read-the-room` isn't version-controlled, so this repo is the only
record of what's actually running.

## Known rough edges

- `docker compose` prints `"UID"`/`"GID" variable is not set` warnings on
  every command — harmless, `.env` doesn't export shell vars, containers run
  as root inside. Pre-existing, not worth fixing unless it causes a real
  permission problem.
- `docker-compose.override.yml` in this repo is **local-dev-only** (remaps
  `web_ui` to a different port and disables `caddy` because the dev
  workstation already runs something else on `:8888`/`:443`). It is
  intentionally not present on the prod container — don't copy it over.
- If `/` redirects to `/auth/login` unexpectedly, check
  `docker compose logs daemon` for `SpotifyOauthError: Refresh token
  revoked` before assuming it's a code problem — the token cache
  (`token_cache/.cache` on the container) can go stale independent of any
  deploy.
