# Phase 20: Repository Hygiene - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the repository safe and non-embarrassing to publish publicly — no credential exposure vectors, no personal data, no stale branding. Five specific mechanical tasks (HYG-01 through HYG-05). New capabilities belong in other phases.

</domain>

<decisions>
## Implementation Decisions

### Module Docstring Rename (HYG-04)
- **D-01:** Replace "Spotify Family Safe Mode" with "Read the Room" in all module docstrings across: `daemon.py`, `content_checker.py`, `skip_client.py`, `drug_scanner.py`, `sexual_content_scanner.py`, `web_ui/main.py`.
- **D-02:** Drop the stale "(Phase N)" annotation from docstrings. e.g., `"""Spotify Family Safe Mode — Core Daemon (Phase 1)."""` becomes `"""Read the Room — Core Daemon."""`
- **D-03:** The FastAPI title in `web_ui/main.py:47` (`FastAPI(title="Spotify Family Safe Mode", ...)`) becomes `FastAPI(title="Read the Room", ...)`.
- **D-04:** Inline code comments that use `family_safe_mode` as a JSON state key name are NOT renamed — they refer to the runtime state key, not the project brand.

### User-Agent Rename (HYG-04)
- **D-05:** `lyrics_service.py:73` — `LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")` becomes `LrcLibAPI(user_agent="ReadTheRoom/1.0")`.

### Personal IP Replacement (HYG-03)
- **D-06:** All occurrences of `192.168.1.164` in `tests/test_sonos_probe.py` replaced with `192.168.1.100`. No other files are affected.

### .dockerignore Scope (HYG-01)
- **D-07:** Create a comprehensive `.dockerignore` at repository root. Excludes: `.env`, `token_cache/`, `state.json`, `data/`, `lyrics_cache.db`, `__pycache__/`, `*.pyc`, `.git/`, `.claude/`, `.planning/`, `tests/`. Standard open-source Docker best practice — Docker build context only includes application source needed to run.

### Git Untrack .claude/ (HYG-02)
- **D-08:** Add `.claude/` to `.gitignore`. Run `git rm --cached -r .claude/` to untrack all currently tracked `.claude/` files without deleting them from disk.

### .env.example Updates (HYG-05)
- **D-09:** Add three documented variables to `.env.example`:
  - `UID` — with comment explaining it's the host user ID for Docker bind-mount ownership (matches `user: "${UID}:${GID}"` in docker-compose.yml)
  - `GID` — with comment explaining it's the host group ID (same reason)
  - `EVENTS_PATH` — with comment explaining it's the path for the events JSONL file (daemon and web_ui both read `EVENTS_PATH` env var, defaulting to `data/events.jsonl`)

### Claude's Discretion
- Exact wording of comments for UID/GID/EVENTS_PATH in .env.example (follow existing comment style)
- Order of new variables in .env.example (append at end or group with related vars)
- Complete list of additional .dockerignore entries beyond the mandated minimum

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Key files to read before planning
- `.planning/REQUIREMENTS.md` — HYG-01 through HYG-05 acceptance criteria
- `.planning/ROADMAP.md` — Phase 20 success criteria (exact grep-verifiable conditions)
- `tests/test_sonos_probe.py` — File containing personal IP to replace
- `lyrics_service.py` — File containing user-agent string to rename
- `web_ui/main.py` — FastAPI title + module docstring + EVENTS_PATH usage
- `daemon.py` — Module docstring + EVENTS_PATH usage
- `.env.example` — File to extend with UID, GID, EVENTS_PATH
- `docker-compose.yml` — Reference for UID/GID/EVENTS_PATH semantics
- `.gitignore` — File to extend with .claude/

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No reusable components — this is pure file manipulation.

### Established Patterns
- `.gitignore` uses inline comments above each section explaining why entries are excluded — follow this style for new entries.
- `.env.example` uses inline comments per-variable explaining semantics — follow this style for UID, GID, EVENTS_PATH.
- Module docstrings are single-line format: `"""Read the Room — [Module description]."""`

### Integration Points
- `git rm --cached -r .claude/` must be run as a shell command (not just editing .gitignore) to actually untrack the files
- `EVENTS_PATH` default is `data/events.jsonl` (confirmed in both daemon.py:43 and web_ui/main.py:54)
- `UID` and `GID` are shell env vars on Linux/macOS — comment should tell new contributors how to set them (e.g., `export UID=$(id -u)`)

</code_context>

<specifics>
## Specific Ideas

- Success criteria from ROADMAP.md are grep-verifiable — planner should include acceptance criteria that match them exactly:
  - `git ls-files .claude/` returns empty after untrack
  - `grep -r "Spotify Family Safe Mode" daemon.py content_checker.py skip_client.py drug_scanner.py sexual_content_scanner.py web_ui/main.py lyrics_service.py` returns nothing
  - `grep "192.168.1.164" tests/test_sonos_probe.py` returns nothing
  - `.env.example` contains `UID`, `GID`, `EVENTS_PATH`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 20-repository-hygiene*
*Context gathered: 2026-04-08*
