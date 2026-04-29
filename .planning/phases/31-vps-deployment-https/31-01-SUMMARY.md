---
phase: 31-vps-deployment-https
plan: 01
subsystem: infra
tags: [caddy, docker, https, tls, letsencrypt, networking]

requires:
  - phase: 30-per-user-daemon-management
    provides: FastAPI app with uid cookie-based routing and OAuth callback

provides:
  - Caddy parameterized for Let's Encrypt TLS on any public domain
  - Docker network mode environment-controlled (host for local, bridge for VPS)
  - .env.example documents all three deployment env vars with VPS-vs-local guidance
  - uid cookie carries Secure=True flag — only transmitted over HTTPS

affects: [future VPS deployment docs, operator onboarding]

tech-stack:
  added: []
  patterns:
    - Caddy env var substitution ({$VAR} syntax) for operator-controlled domain and upstream
    - Docker Compose ${VAR:-default} for environment-controlled network mode

key-files:
  created: []
  modified:
    - Caddyfile
    - docker-compose.yml
    - .env.example
    - web_ui/main.py

key-decisions:
  - "{$APP_DOMAIN} replaces hardcoded LAN IP — operator sets APP_DOMAIN= in .env for any domain"
  - "tls internal removed — Caddy auto-provisions Let's Encrypt when APP_DOMAIN is a real domain"
  - "NETWORK_MODE=bridge for VPS (no Sonos); unset defaults to host for local deployments"
  - "WEB_UI_UPSTREAM=web_ui:8888 on bridge; localhost:8888 default for host networking"
  - "secure=True now safe because Caddy terminates TLS before the cookie is set"

patterns-established:
  - "Caddyfile env var substitution: {$VAR_NAME} for required, {$VAR:-default} for optional"
  - "docker-compose NETWORK_MODE pattern: single env var controls host vs bridge across all services"

requirements-completed:
  - DEPLOY-01
  - DEPLOY-02
  - DEPLOY-03

duration: 8min
completed: 2026-04-28
---

# Phase 31: VPS Deployment + HTTPS Summary

**Caddy upgraded from self-signed LAN config to parameterized Let's Encrypt TLS; Docker network mode made env-controlled for VPS/local dual-deployment; uid cookie secured with Secure=True**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-28T00:00:00Z
- **Completed:** 2026-04-28T00:08:00Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- Caddyfile now uses `{$APP_DOMAIN}` and `{$WEB_UI_UPSTREAM:-localhost:8888}` — operators set APP_DOMAIN=yourdomain.com and Caddy auto-provisions a Let's Encrypt cert with no other config
- All three Docker services (daemon, web_ui, caddy) use `${NETWORK_MODE:-host}` — VPS sets `NETWORK_MODE=bridge`, local leaves unset for Sonos UPnP host networking
- `.env.example` gains a VPS deployment block at the top with APP_DOMAIN, WEB_UI_UPSTREAM, and NETWORK_MODE guidance; SPOTIFY_REDIRECT_URI example updated from hardcoded LAN IP to `yourdomain.com` pattern
- `secure=True` added to uid `set_cookie` — browser will only transmit the cookie over HTTPS, which is now guaranteed by Caddy TLS termination

## Task Commits

1. **Task 1: Parameterize Caddyfile for Let's Encrypt** — `3d3cb2c` (feat)
2. **Task 2: Environment-controlled network_mode** — `3034daa` (feat)
3. **Task 3: VPS vars in .env.example** — `34896e8` (docs)
4. **Task 4: secure=True on uid cookie** — `b04d683` (feat)

## Files Created/Modified
- `Caddyfile` — replaced hardcoded IP + `tls internal` with `{$APP_DOMAIN}` / `{$WEB_UI_UPSTREAM:-localhost:8888}`
- `docker-compose.yml` — `network_mode: ${NETWORK_MODE:-host}` on all three services (was hardcoded `host`)
- `.env.example` — new VPS deployment section; SPOTIFY_REDIRECT_URI updated to domain pattern
- `web_ui/main.py` — `secure=True` replaces the Phase 31 deferred comment on `set_cookie`

## Decisions Made
- `tls internal` removed without replacement — Caddy's ACME auto-provisioning activates automatically for real domains; no extra config needed
- Used `NETWORK_MODE` (values: `host`/`bridge`) not a boolean flag — Docker Compose requires direct value substitution, cannot do boolean-to-value logic
- `192.168.1.220` preserved only in a comment in `.env.example` as a local-server example; all active lines use `yourdomain.com`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**VPS deployment requires operator action before first `docker compose up`:**

1. Point your domain's A record to the VPS IP
2. In `.env`, set:
   ```
   APP_DOMAIN=yourdomain.com
   WEB_UI_UPSTREAM=web_ui:8888
   NETWORK_MODE=bridge
   SPOTIFY_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```
3. Register `https://yourdomain.com/auth/callback` in your Spotify app dashboard
4. Run `docker compose up -d` — Caddy will auto-provision the Let's Encrypt cert

Local home server: leave `NETWORK_MODE` unset (defaults to `host` for Sonos UPnP).

## Self-Check: PASSED

- `grep APP_DOMAIN Caddyfile` → 1 match ✓
- `grep WEB_UI_UPSTREAM Caddyfile` → 1 match ✓
- `grep 'tls internal' Caddyfile` → 0 matches ✓
- `grep -c NETWORK_MODE docker-compose.yml` → 3 ✓
- `grep 'network_mode: host$' docker-compose.yml` → 0 ✓
- `grep APP_DOMAIN= .env.example` → 3 matches ✓
- `grep 'SPOTIFY_REDIRECT_URI=https://yourdomain.com' .env.example` → 1 ✓
- `grep 'secure=True' web_ui/main.py` → 1 ✓
- `python -c "import ast; ast.parse(open('web_ui/main.py').read())"` → OK ✓

## Next Phase Readiness

Phase 31 is the final infrastructure phase for milestone v1.8. The service is now fully deployable to a public VPS with automatic HTTPS. No blockers for milestone completion.

---
*Phase: 31-vps-deployment-https*
*Completed: 2026-04-28*
