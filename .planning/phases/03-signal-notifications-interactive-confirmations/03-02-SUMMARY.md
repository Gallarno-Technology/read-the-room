---
phase: 03-signal-notifications-interactive-confirmations
plan: 02
subsystem: ui
tags: [html, css, javascript, sse, fastapi, docker-compose, uvicorn]

# Dependency graph
requires:
  - phase: 03-signal-notifications-interactive-confirmations
    provides: web_ui/main.py FastAPI app with /events SSE, GET /fsm, POST /fsm endpoints and skip_event_queue

provides:
  - web_ui/templates/index.html: full dark-theme dashboard HTML/CSS/JS (450 lines)
  - web_ui/Dockerfile: container image for web_ui FastAPI service (uvicorn port 8888)
  - docker-compose.yml web_ui service: runs alongside daemon, network_mode host, state.json bind-mount
  - Makefile ui-logs target for tailing web_ui logs
  - .env.example WEB_UI_PORT documentation

affects:
  - Phase 4 hardening (docker-compose.yml consumed by any future infra work)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Single-file HTML dashboard: all CSS and JS embedded in one template, no build step
    - FSM initial state injection via Python string replace of __FSM_INITIAL__ placeholder
    - EventSource SSE client with onopen/onerror/onmessage handlers for connected/reconnecting/data states
    - Optimistic UI update with rollback on HTTP error for FSM toggle

key-files:
  created:
    - web_ui/templates/index.html
    - web_ui/Dockerfile
  modified:
    - docker-compose.yml
    - .env.example
    - Makefile

key-decisions:
  - "HTML/CSS/JS is fully self-contained in one template file — no external JS files, no CDN libraries, zero third-party browser code"
  - "FSM initial state uses __FSM_INITIAL__ placeholder replaced by main.py at serve time — avoids a separate /fsm API call on page load"
  - "web_ui Dockerfile uses COPY . . from project root so daemon.py is importable at /app/daemon.py (required for in-process queue import)"
  - "docker-compose web_ui service has no ports: mapping — network_mode: host exposes uvicorn port 8888 directly on host"

patterns-established:
  - "Placeholder injection: Python template.replace('__TOKEN__', value) pattern for server-side HTML rendering without a template engine"
  - "SSE status dot: CSS class swap (connected / reconnecting) driven by EventSource lifecycle events"

requirements-completed: [SIG-02, SIG-03, FSM-03]

# Metrics
duration: 2min
completed: 2026-04-02
---

# Phase 03 Plan 02: Dashboard HTML, Dockerfile, and docker-compose Wiring Summary

**Dark-theme single-page dashboard with FSM toggle, SSE skip feed (four badge variants), five-skip warning banner, wired into docker-compose as a second service alongside the daemon**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-02T03:24:14Z
- **Completed:** 2026-04-02T03:26:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Delivered complete 450-line index.html: dark theme with all 11 CSS color tokens, FSM toggle with optimistic update/rollback, SSE skip feed with four reason badge variants, five-skip warning banner (hidden by default, dismissible), SSE status indicator (connected/reconnecting), all copywriting verbatim per UI-SPEC.md
- Created web_ui/Dockerfile using python:3.12-slim with COPY . . so daemon.py is importable for in-process queue sharing
- Added web_ui service to docker-compose.yml (network_mode: host, state.json bind-mount, restart: always) making `docker compose up -d` the only command needed to start both services

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dashboard HTML template and web_ui Dockerfile** - `2785f44` (feat)
2. **Task 2: Wire web_ui service into docker-compose.yml, .env.example, and Makefile** - `4eb84ae` (feat)

## Files Created/Modified

- `web_ui/templates/index.html` - Single-page dashboard: dark theme, FSM toggle (two states), SSE skip feed with badges, five-skip banner, SSE status dot, all JS inline
- `web_ui/Dockerfile` - python:3.12-slim image, pip install requirements.txt, COPY . ., uvicorn on port 8888
- `docker-compose.yml` - web_ui service added with build context, network_mode: host, state.json bind-mount, restart: always
- `.env.example` - WEB_UI_PORT=8888 documented
- `Makefile` - ui-logs target added, .PHONY updated

## Decisions Made

- No separate /fsm API call on page load: the server injects current FSM state into the HTML via `__FSM_INITIAL__` replacement in main.py — the button renders correctly on first paint without an extra round-trip
- COPY . . in Dockerfile (not COPY web_ui/ .) — required so daemon.py is on the PYTHONPATH at /app/daemon.py, enabling in-process queue import (the in-process queue sharing design from Plan 03-01)
- No ports: mapping in docker-compose web_ui service — network_mode: host makes this unnecessary; port 8888 is directly accessible on the host

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — the `GET /` dashboard stub from Plan 03-01 is now resolved by web_ui/templates/index.html.

## Next Phase Readiness

- Phase 3 is complete: daemon + web_ui both start with `docker compose up -d`
- http://localhost:8888 serves the full dashboard immediately after auth
- FSM toggle, skip feed, and five-skip banner all wired end-to-end via SSE
- No blockers for Phase 4 (hardening)

---
*Phase: 03-signal-notifications-interactive-confirmations*
*Completed: 2026-04-02*
