# Contributing to Read the Room

Thanks for your interest. This document covers how the project is structured,
how to run it locally, and how to submit changes.

This repository is proprietary software. A cloud version is planned as a separate service in its own repository. No contributor license agreement is required for this repository.

## Project layout

| Path | Purpose |
|------|---------|
| `daemon.py` | Main polling loop — monitors Spotify playback and triggers skips |
| `content_checker.py` | Profanity and lyric scan logic — orchestrates all content scanners |
| `skip_client.py` | Sonos UPnP skip via SoCo; falls back to Spotify API if Sonos is unavailable |
| `lyrics_service.py` | LRCLIB lyric lookup with SQLite cache (`lyrics_cache.db`) |
| `web_ui/` | FastAPI dashboard (templates, `main.py`) + single-user Spotify OAuth (`/auth/login`, `/auth/callback`) served on port 8888 |
| `tests/` | pytest test suite — fully mocked, no real Spotify credentials or Docker needed |
| `docker-compose.yml` | Three services: `daemon`, `web_ui`, and `caddy` (TLS reverse proxy) |
| `Makefile` | Developer shortcuts (`make setup`, `make up`, `make logs`, `make daemon-logs`, `make ui-logs`, etc.) |
| `.env.example` | Template for all environment variables with inline explanations |
| `PROXMOX.md` | Sonos SSDP fix for Proxmox LXC users |

## Local dev setup

There are two tracks depending on what you want to do.

### Running the service (Docker)

```bash
make setup      # creates bind-mount files, copies .env.example → .env
# edit .env — fill in SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
make up         # starts daemon + web_ui + caddy in the background
```

Dashboard is available at [http://localhost:8888](http://localhost:8888). On first visit it
redirects you to Spotify to authorize (one time); the callback writes the token cache that the
`daemon` container then picks up.

### Running the test suite (host Python)

Tests are fully mocked — no Spotify credentials, no Sonos hardware, no Docker required.

```bash
pip install -r requirements.txt
pytest tests/
```

Requires Python 3.11+.

## Running tests

```bash
pytest tests/
```

All tests live in `tests/`. The suite is fast (< 10 seconds) and requires no external services.
To run a specific test file: `pytest tests/test_content_checker.py`

## Filing issues

Please include:

- OS and Docker version (`docker compose version`)
- Relevant log output (`make logs` for the daemon, `make ui-logs` for the dashboard)
- What you expected to happen vs. what actually happened

For Sonos discovery problems, include your network setup (router model, whether you're running
in a VM or container host like Proxmox).

## Submitting a PR

1. Fork the repository and create a branch from `main`.
2. Make your changes. Run `pytest tests/` to confirm nothing is broken.
3. Open a pull request against `main` with a brief description of what changed and why.

CI will run the test suite automatically on your PR (GitHub Actions — configured in Phase 22).
