# Phase 5: Deployment & Documentation - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Any developer with Docker can clone the repo and have the service running — and the service survives reboots, hangs silently, and updates cleanly. Covers: clone-and-run README, Sonos network requirements, boot persistence documentation and verification, docker-compose.yml healthcheck, and safe update workflow. No new features, no UI changes, no new env vars beyond what's already in .env.example.

</domain>

<decisions>
## Implementation Decisions

### README Target Reader & Structure
- **D-01:** Target reader is "me, returning after weeks away" — assume Docker familiarity and project-level amnesia. Optimize for re-setup speed over first-timer hand-holding.
- **D-02:** Quick-start block first (top of README), then detail sections below. Structure: Quick Start → Prerequisites → Updating. Skimmable.
- **D-03:** Quick-start uses explicit docker commands (not Makefile targets). Raw `docker compose run --rm -it daemon python setup_auth.py` and `docker compose up -d` — no Makefile dependency. The existing Makefile targets remain available but are not the canonical flow in the README.
- **D-04:** README sections below quick-start: Prerequisites (Docker, docker compose, Spotify app registration, UID:GID) and Updating (`git pull && docker compose up -d --build`). No troubleshooting section, no configuration reference (`.env.example` is self-documenting).
- **D-05:** Sonos setup is NOT a separate README section. Proxmox/LXC multicast notes go in a separate `PROXMOX.md` file, linked from the quick-start or prerequisites where relevant.

### Proxmox/LXC Multicast Documentation
- **D-06:** High-level note only — no specific nftables commands or bridge config steps. "Proxmox LXC containers require multicast bridge forwarding to be enabled for Sonos SSDP discovery. See your Proxmox documentation or `PROXMOX.md` for guidance." Points reader in the right direction without risking outdated or environment-specific commands.
- **D-07:** Proxmox notes live in `PROXMOX.md` (repo root), linked from README where Sonos is mentioned. Keeps README clean. Content: what multicast forwarding is, why it's needed for SSDP, high-level note about enabling it in Proxmox, and the `SONOS_SPEAKER_IPS` fallback as an alternative if bridge config isn't possible.

### Healthcheck (Claude's Discretion)
- **D-08:** Add a Docker healthcheck to `docker-compose.yml` for the daemon service. Check whether the daemon Python process is alive and recently active. Recommended approach: `test: ["CMD", "python", "-c", "import os, time; f='.healthcheck'; assert time.time()-os.stat(f).st_mtime<60"]` where the daemon touches a `.healthcheck` file each poll cycle. Interval 30s, timeout 10s, retries 3, start_period 15s. On failure: Docker restarts the container automatically (relies on `restart: always`).
- **D-09:** Apply healthcheck to `daemon` service only — `web_ui` service does not need one for v1.

### Update Workflow (Claude's Discretion)
- **D-10:** Update procedure is: `git pull && docker compose up -d --build`. Document in README's Updating section. No `make update` target needed. State explicitly that bind-mounted data files (`state.json`, `lyrics_cache.db`, `token_cache/`, `data/`) are on the host and survive rebuilds.
- **D-11:** No migration tooling in Phase 5. The bind-mount pattern means no data is inside containers — rebuilding the image is safe. If a future phase adds a new bind-mount file, `make setup` is the right place to pre-create it.

### Claude's Discretion
- Exact wording and formatting of README sections
- Healthcheck file path and daemon-side touch implementation (can be in `poll_loop()` or a wrapper)
- Whether to add a `healthcheck` to `web_ui/Dockerfile` as well (recommended: no — start simple)
- PROXMOX.md depth and format

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing infrastructure
- `docker-compose.yml` — services, restart policy, bind mounts, network_mode; healthcheck block goes here
- `.env.example` — all env vars with comments; README points to this file, does not duplicate it
- `Makefile` — existing setup/auth/up/down targets; README references docker commands directly (D-03) but Makefile stays

### Requirements
- `.planning/REQUIREMENTS.md` — DEPL-01 through DEPL-05 (all Phase 5 requirements)

### Project context
- `.planning/PROJECT.md` — milestone goal, Proxmox deployment context, Sonos discovery decisions

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Makefile:setup` — pre-creates bind-mount files; README can reference this as the pre-requisite step or inline its commands
- `.env.example` — well-commented; README quick-start points to it ("copy and edit")
- `daemon.py:poll_loop()` — healthcheck touch file can be added here (one line per loop iteration)

### Established Patterns
- Bind-mount pattern: all persistent data on host (`state.json`, `lyrics_cache.db`, `token_cache/`, `data/`); rebuild-safe by design
- `restart: always` already set — healthcheck piggybacks on this to trigger auto-restart on failure
- `user: "${UID}:${GID}"` in compose — bind-mount files written by container are host-user-owned

### Integration Points
- `docker-compose.yml` — healthcheck block added to `daemon:` service definition
- `daemon.py:poll_loop()` — one `Path('.healthcheck').touch()` call per iteration for healthcheck mechanism
- `README.md` — new file at repo root; no existing one to update
- `PROXMOX.md` — new file at repo root; linked from README

</code_context>

<specifics>
## Specific Ideas

- README is for "me, returning after weeks away" — terse, assumes Docker knowledge, quick-start leads with raw docker commands (not Makefile)
- Proxmox/LXC section stays high-level — user doesn't want speculative firewall rules they haven't verified themselves. Point to docs, offer the `SONOS_SPEAKER_IPS` escape hatch as the practical workaround.

</specifics>

<deferred>
## Deferred Ideas

- Troubleshooting section in README — not selected; common issues are inferable from .env.example and logs
- Configuration reference section — .env.example is self-documenting, no separate reference needed
- Healthcheck for web_ui service — overkill for v1, can add later
- make update target — pure documentation is sufficient; no Makefile change needed
- Specific nftables/bridge commands for Proxmox — too environment-specific without verified steps; high-level note + link is safer

</deferred>

---

*Phase: 05-deployment-documentation*
*Context gathered: 2026-04-02*
