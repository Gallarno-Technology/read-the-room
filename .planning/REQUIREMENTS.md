# Requirements: Read the Room

**Defined:** 2026-04-16
**Milestone:** v1.8 — Multi-User Beta
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.8 Requirements

Beta multi-user support for up to 5 users (Spotify dev mode cap). Manual operator
onboarding by design — friction is a quality filter and a conversation touchpoint.
Cookie-based uid routing; per-user daemon isolation; server-side OAuth callback.

### Isolation

- [ ] **ISOL-01**: Provisioned user has an isolated data directory (`users/{uid}/`) containing their own `state.json`, `data/events.jsonl`, `data/now_playing.json`, and `token_cache/`
- [ ] **ISOL-02**: A flat registry (`users.json`) maps each uid to name and `created_at` timestamp
- [ ] **ISOL-03**: `lyrics_cache.db` is shared across all users, keyed by Spotify track ID

### Operator

- [x] **OPS-01**: Operator can run `manage_users.py generate-url <name>` to print a new uid and Spotify OAuth URL with that uid baked into the `state` parameter
- [x] **OPS-02**: Operator can run `manage_users.py remove <uid>` to stop the user's daemon, delete their data directory, and remove their registry entry

### Web Routing

- [ ] **ROUTE-01**: All FastAPI route handlers resolve a `UserContext` (per-user file paths) from a `uid` httpOnly cookie on every request
- [ ] **ROUTE-02**: SSE `/events` endpoint spawns a per-user file tail task on first connection rather than maintaining a single global tail at server startup

### OAuth Onboarding

- [ ] **AUTH-01**: `GET /auth/callback` receives the Spotify OAuth redirect, validates the `state` parameter matches the pending uid, exchanges the code for a token, writes the token to `users/{uid}/token_cache/`, creates the user's data dirs, and updates `users.json`
- [ ] **AUTH-02**: The uid travels through the Spotify authorization flow via the OAuth `state` parameter, preventing callback routing collisions
- [ ] **AUTH-03**: Server automatically spawns the user's daemon process after the token is successfully written to disk

### Process Management

- [ ] **PROC-01**: `web_ui` spawns per-user daemon processes via `asyncio.create_subprocess_exec` with uid-specific env vars (`STATE_PATH`, `EVENTS_PATH`, `LYRICS_DB_PATH`, `SPOTIFY_CACHE_PATH`)
- [ ] **PROC-02**: A supervisor coroutine monitors each user's daemon and restarts it automatically on unexpected exit
- [ ] **PROC-03**: `POLL_INTERVAL_SECONDS` defaults to `3` in multi-user mode to reduce Spotify API call rate across N daemons
- [ ] **PROC-04**: On `web_ui` startup, all users listed in `users.json` have their daemon processes re-launched automatically

### Deployment

- [ ] **DEPLOY-01**: `docker-compose.yml` includes a Caddy service (`caddy:2-alpine`) with a Caddyfile that terminates TLS automatically via Let's Encrypt and proxies to `web_ui`
- [ ] **DEPLOY-02**: `network_mode: host` is controlled by a `SONOS_ENABLED` env var — VPS deployments set `false`, local home-server deployments keep `true`
- [ ] **DEPLOY-03**: `SPOTIFY_REDIRECT_URI` env var and Spotify Developer Dashboard redirect URI are set to the HTTPS callback URL

### Frontend

- [ ] **UI-01**: First visit with no uid cookie shows a full-page ID entry gate prompting for an access code
- [ ] **UI-02**: On valid ID entry or post-OAuth callback, server sets an httpOnly uid cookie and JS writes uid to `localStorage`; subsequent visits load the dashboard directly without re-entering the code
- [ ] **UI-03**: Invalid or unknown uid entered at the ID gate shows a clear error message rather than a silent failure
- [ ] **UI-04**: Post-OAuth callback redirects browser to the dashboard where UI-02 cookie and localStorage persistence runs on arrival

## v2+ Requirements

- Self-service OAuth onboarding (removes operator from the loop)
- Admin web UI for operator (list users, daemon status, remove)
- Per-user daemon start/stop control from operator CLI
- Quota extension path for >5 users (BYOC model or Spotify Extended Quota)
- Per-user custom filter profiles beyond the 4 presets

## Out of Scope

| Feature | Reason |
|---------|--------|
| >5 concurrent users | Spotify dev mode hard cap (March 2026); BYOC path deferred to v2 |
| User passwords / JWT auth | Opaque uid is sufficient auth for 5-person trusted beta |
| Self-serve signup UI | Manual onboarding is intentional — friction filters for quality |
| Admin web panel | Operator CLI covers 5-user management; web UI is over-engineering |
| Sonos support on VPS | LAN-only; VPS daemon uses Spotify API skip only |
| Per-user Spotify app registrations | Single app with 5-user dev mode covers this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ISOL-01 | Phase 27 | Pending |
| ISOL-02 | Phase 27 | Pending |
| ISOL-03 | Phase 27 | Pending |
| OPS-01 | Phase 27 | Complete |
| OPS-02 | Phase 27 | Complete |
| ROUTE-01 | Phase 28 | Pending |
| ROUTE-02 | Phase 28 | Pending |
| AUTH-01 | Phase 29 | Pending |
| AUTH-02 | Phase 29 | Pending |
| AUTH-03 | Phase 29 | Pending |
| PROC-01 | Phase 30 | Pending |
| PROC-02 | Phase 30 | Pending |
| PROC-03 | Phase 30 | Pending |
| PROC-04 | Phase 30 | Pending |
| DEPLOY-01 | Phase 31 | Pending |
| DEPLOY-02 | Phase 31 | Pending |
| DEPLOY-03 | Phase 31 | Pending |
| UI-01 | Phase 32 | Pending |
| UI-02 | Phase 32 | Pending |
| UI-03 | Phase 32 | Pending |
| UI-04 | Phase 32 | Pending |

**Coverage:**
- v1.8 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after initial definition*
