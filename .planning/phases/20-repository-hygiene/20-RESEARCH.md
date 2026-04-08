# Phase 20: Repository Hygiene - Research

**Researched:** 2026-04-08
**Domain:** Git hygiene, Docker security, source code branding cleanup
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module Docstring Rename (HYG-04)**
- D-01: Replace "Spotify Family Safe Mode" with "Read the Room" in all module docstrings across: `daemon.py`, `content_checker.py`, `skip_client.py`, `drug_scanner.py`, `sexual_content_scanner.py`, `web_ui/main.py`.
- D-02: Drop the stale "(Phase N)" annotation from docstrings. e.g., `"""Spotify Family Safe Mode — Core Daemon (Phase 1)."""` becomes `"""Read the Room — Core Daemon."""`
- D-03: The FastAPI title in `web_ui/main.py:47` (`FastAPI(title="Spotify Family Safe Mode", ...)`) becomes `FastAPI(title="Read the Room", ...)`.
- D-04: Inline code comments that use `family_safe_mode` as a JSON state key name are NOT renamed — they refer to the runtime state key, not the project brand.

**User-Agent Rename (HYG-04)**
- D-05: `lyrics_service.py:73` — `LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")` becomes `LrcLibAPI(user_agent="ReadTheRoom/1.0")`.

**Personal IP Replacement (HYG-03)**
- D-06: All occurrences of `192.168.1.164` in `tests/test_sonos_probe.py` replaced with `192.168.1.100`. No other files are affected.

**.dockerignore Scope (HYG-01)**
- D-07: Create a comprehensive `.dockerignore` at repository root. Excludes: `.env`, `token_cache/`, `state.json`, `data/`, `lyrics_cache.db`, `__pycache__/`, `*.pyc`, `.git/`, `.claude/`, `.planning/`, `tests/`. Standard open-source Docker best practice — Docker build context only includes application source needed to run.

**Git Untrack .claude/ (HYG-02)**
- D-08: Add `.claude/` to `.gitignore`. Run `git rm --cached -r .claude/` to untrack all currently tracked `.claude/` files without deleting them from disk.

**.env.example Updates (HYG-05)**
- D-09: Add three documented variables to `.env.example`:
  - `UID` — with comment explaining it's the host user ID for Docker bind-mount ownership (matches `user: "${UID}:${GID}"` in docker-compose.yml)
  - `GID` — with comment explaining it's the host group ID (same reason)
  - `EVENTS_PATH` — with comment explaining it's the path for the events JSONL file (daemon and web_ui both read `EVENTS_PATH` env var, defaulting to `data/events.jsonl`)

### Claude's Discretion
- Exact wording of comments for UID/GID/EVENTS_PATH in .env.example (follow existing comment style)
- Order of new variables in .env.example (append at end or group with related vars)
- Complete list of additional .dockerignore entries beyond the mandated minimum

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYG-01 | A `.dockerignore` exists so live OAuth tokens, `.env`, and runtime data directories are excluded from Docker build context | Verified: `.dockerignore` is absent; `Dockerfile` uses `COPY . .` which bakes everything in without a dockerignore |
| HYG-02 | `.claude/` directory is untracked from git and added to `.gitignore` | Verified: 217 `.claude/` files are currently tracked; `.gitignore` does not include `.claude/` |
| HYG-03 | Personal IP `192.168.1.164` replaced with generic placeholder (`192.168.1.100`) in `tests/test_sonos_probe.py` | Verified: 5 occurrences of `192.168.1.164` in `tests/test_sonos_probe.py` (lines 47, 58, 70, 82, 83, 99, 113); also appears in `.env` (not in scope per D-06) |
| HYG-04 | "Spotify Family Safe Mode" replaced with "Read the Room" in all module docstrings and source strings | Verified: 7 occurrences across `daemon.py`, `content_checker.py`, `skip_client.py`, `drug_scanner.py`, `sexual_content_scanner.py`, `web_ui/main.py` (×2 including FastAPI title), and user-agent string in `lyrics_service.py:73` |
| HYG-05 | `.env.example` updated to include `UID`, `GID`, and `EVENTS_PATH` with explanatory comments | Verified: `.env.example` exists but lacks `UID`, `GID`, `EVENTS_PATH`; these variables are used in `docker-compose.yml` and `web_ui/main.py:54` |
</phase_requirements>

---

## Summary

Phase 20 is five discrete file-edit tasks with no external dependencies, no new libraries, and no architectural decisions. The work is mechanical: create one file (`.dockerignore`), edit three source files for branding, edit one test file for IP replacement, edit one config example file, and run one git command to untrack `.claude/`.

The critical gate constraint from STATE.md holds: personal IPs and credential exposure vectors are irreversible once forks appear. This phase must be complete before any Phase 21-22 work begins.

The `.env` file also contains the real IP (`192.168.1.164`) but it is gitignored already. Per D-06, only `tests/test_sonos_probe.py` is in scope for replacement. The planner should not add a task for `.env` modification.

**Primary recommendation:** Execute five targeted edits in dependency order: (1) `.dockerignore` creation, (2) `.gitignore` + `git rm --cached`, (3) IP replacement in test file, (4) branding rename across six source files, (5) `.env.example` extension.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| git | system | Version control operations (untracking files) | Already installed; `git rm --cached` is the canonical untrack command |

### Supporting

No new libraries required. All work uses existing tooling: standard file editing and git CLI.

**Installation:** None required.

## Architecture Patterns

### Recommended Task Structure

Five independent tasks — each maps 1:1 to a requirement. Tasks 3 and 4 can be batched into a single "source file cleanup" task since they share the branding theme, but ordering within a task must respect D-04 (do not rename `family_safe_mode` JSON key references).

```
Phase 20 tasks:
├── Task 1: Create .dockerignore (HYG-01)
├── Task 2: Untrack .claude/ from git (HYG-02)
├── Task 3: Replace personal IP in test file (HYG-03)
├── Task 4: Rename branding in source files (HYG-04)
└── Task 5: Update .env.example (HYG-05)
```

### Pattern 1: .dockerignore — COPY . . with exclusions

**What:** A `.dockerignore` file at the build context root tells Docker which files to exclude from the build context sent to the daemon. Works analogously to `.gitignore`.
**When to use:** Any time `Dockerfile` uses `COPY . .` — without it, ALL files including secrets are baked in.
**Critical detail:** Both the root `Dockerfile` and `web_ui/Dockerfile` use `COPY . .`. The root `.dockerignore` applies to both build contexts because `docker-compose.yml` sets `context: .` for both services. A single `.dockerignore` at root covers both.

```dockerfile
# Example .dockerignore entries
.env
token_cache/
state.json
data/
lyrics_cache.db
__pycache__/
*.pyc
.git/
.claude/
.planning/
tests/
```

### Pattern 2: git rm --cached (untracking without deletion)

**What:** `git rm --cached -r .claude/` removes files from the git index (stops tracking them) without deleting them from the working directory.
**Critical sequence:** `.gitignore` entry MUST be written first, then `git rm --cached` run. Reversing this leaves a window where the files are untracked but not gitignored — a `git add .` in that window would re-track them.
**Verification:** After running, `git ls-files .claude/` must return empty.

```bash
# Correct order
# 1. Add .claude/ to .gitignore (file edit)
# 2. Run:
git rm --cached -r .claude/
# 3. Verify:
git ls-files .claude/  # must return empty
```

### Pattern 3: Module docstring format (established in project)

**What:** Single-line docstrings: `"""Read the Room — [Module description]."""`
**Current state verified:**
- `daemon.py:2` — `"""Spotify Family Safe Mode — Core Daemon (Phase 1)."""` → `"""Read the Room — Core Daemon."""`
- `content_checker.py:2` — `"""Content filtering orchestrator for Spotify Family Safe Mode (Phase 2).` → `"""Read the Room — Content filtering orchestrator.` (multi-line, keep rest of docstring)
- `skip_client.py:2` — `"""Skip client abstractions for Spotify Family Safe Mode (Phase 2).` → `"""Read the Room — Skip client abstractions.`
- `drug_scanner.py:2` — `"""Drug reference scanner for Spotify Family Safe Mode.` → `"""Read the Room — Drug reference scanner.`
- `sexual_content_scanner.py:2` — `"""Sexual content scanner for Spotify Family Safe Mode.` → `"""Read the Room — Sexual content scanner.`
- `web_ui/main.py:1` — `"""Spotify Family Safe Mode — Web UI Service (Phase 3).` → `"""Read the Room — Web UI Service.`
- `web_ui/main.py:47` — `FastAPI(title="Spotify Family Safe Mode", ...)` → `FastAPI(title="Read the Room", ...)`
- `lyrics_service.py:73` — `LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")` → `LrcLibAPI(user_agent="ReadTheRoom/1.0")`

**D-04 boundary:** Lines referencing `family_safe_mode` as a JSON key (state file key, FSM toggle responses) are NOT renamed. These are runtime data identifiers, not branding.

### Pattern 4: .env.example comment style

**Existing style (observed):**
```bash
# Sonos speaker IP addresses — optional escape hatch for networks where SSDP/multicast is
# blocked (firewalls, Proxmox LXC without bridge multicast forwarding). SSDP is used
# automatically when this is unset. Format: "Room Name=IP,Other Room=IP"
```

New entries should follow the same pattern: multi-line block comment above the variable, explaining purpose and semantics. UID/GID need to explain the Linux shell variable source.

### Anti-Patterns to Avoid

- **Editing `.env`:** The `.env` file contains `192.168.1.164` but is gitignored — do not modify it. Only `tests/test_sonos_probe.py` is in scope (D-06).
- **Renaming `family_safe_mode` JSON key:** The state file uses `family_safe_mode` as a key name. This is a runtime contract, not branding (D-04).
- **Running `git rm --cached` before editing `.gitignore`:** Creates a window where files are untracked but re-addable. Always write `.gitignore` first.
- **Forgetting `lyrics_service.py`:** The user-agent string (line 73) is not a docstring — it is in the constructor body. It is still in scope for HYG-04.
- **Missing the FastAPI title:** `web_ui/main.py` has TWO occurrences: the module docstring (line 1) and `FastAPI(title=...)` (line 47). Both must be updated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker build context security | Custom pre-build script | `.dockerignore` file | Docker natively reads `.dockerignore` before sending build context; scripts can be skipped |
| Git file untracking | Manual `git rm` of individual files | `git rm --cached -r .claude/` | Recursive flag handles all 217 files in one command |

**Key insight:** All five tasks in this phase are solved by standard tools with no custom logic required.

## Runtime State Inventory

> Included because this phase involves renaming "Spotify Family Safe Mode" brand string across source files.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `state.json` uses key `family_safe_mode` — this is a runtime state key, NOT the project brand name | None — D-04 explicitly excludes JSON key names from rename |
| Live service config | `docker-compose.yml` uses `title` from `web_ui/main.py` (FastAPI) — FastAPI title is only displayed in API docs (disabled: `docs_url=None`) | Code edit only (HYG-04); no deployed service state to update |
| OS-registered state | None — no task scheduler or systemd unit names reference the old brand | None — verified by inspection |
| Secrets/env vars | `.env` contains `SONOS_SPEAKER_IPS=Living Room=192.168.1.164` (personal IP) — `.env` is gitignored | None — `.env` is not committed; only `tests/test_sonos_probe.py` is in scope (D-06) |
| Build artifacts | `.venv/` present but not committed; no egg-info or compiled artifacts with brand name | None |

**Nothing found requiring data migration.** All changes are code edits only. The `family_safe_mode` JSON key in `state.json` is intentionally preserved per D-04.

## Common Pitfalls

### Pitfall 1: Double-occurrence in web_ui/main.py
**What goes wrong:** Editor replaces only the module docstring in `web_ui/main.py` and misses the `FastAPI(title=...)` call on line 47.
**Why it happens:** They look like different categories of change (docstring vs. constructor arg) so a non-exhaustive review misses one.
**How to avoid:** Verify with `grep "Spotify Family Safe Mode" web_ui/main.py` returning zero results after both edits.
**Warning signs:** Acceptance check `grep -r "Spotify Family Safe Mode" ...` still matches `web_ui/main.py`.

### Pitfall 2: .env also contains the personal IP
**What goes wrong:** Reviewer sees `.env` contains `192.168.1.164` and adds a task to fix it, violating D-06 scope and touching a file that should not be in planning scope.
**Why it happens:** The grep audit surfaced the IP in `.env` alongside `tests/test_sonos_probe.py`.
**How to avoid:** Decision D-06 explicitly limits scope to `tests/test_sonos_probe.py` only. `.env` is already gitignored and not committed.
**Warning signs:** Any plan task targeting `.env` for IP replacement.

### Pitfall 3: git rm --cached before .gitignore edit
**What goes wrong:** Files are removed from git index, then the next `git add .` or auto-staging re-adds them before `.gitignore` entry is committed.
**Why it happens:** Operations run out of order.
**How to avoid:** Always: (1) edit `.gitignore`, (2) commit or stage `.gitignore`, (3) run `git rm --cached -r .claude/`, (4) commit removal.
**Warning signs:** `git ls-files .claude/` returns results after the untrack step.

### Pitfall 4: Replacing only one type of IP occurrence in test file
**What goes wrong:** The IP appears as both a mock value (`mock_speaker.ip_address = "192.168.1.164"`) and as a string in assertions (`"192.168.1.164"`). Replacing only one type causes test failures.
**Why it happens:** The test file has 7 occurrences across different line types (line 47, 58, 70, 82, 83, 99, 113).
**How to avoid:** Replace ALL occurrences, then verify with `grep "192.168.1.164" tests/test_sonos_probe.py` returning zero.
**Warning signs:** Post-replacement grep still finds matches.

### Pitfall 5: Accidentally renaming family_safe_mode JSON key references
**What goes wrong:** A broad find-replace on "family_safe_mode" breaks the FSM toggle endpoint which reads/writes `{"family_safe_mode": bool}` from/to `state.json`.
**Why it happens:** D-04 is easily forgotten in a bulk rename operation.
**How to avoid:** Only replace the brand string "Spotify Family Safe Mode" (with spaces, proper case). The snake_case `family_safe_mode` key is a different string entirely.
**Warning signs:** FSM toggle (`POST /fsm`) returns mismatched keys after deployment.

## Code Examples

Verified from direct source inspection:

### Current state — exact strings to replace

```python
# daemon.py:2
"""Spotify Family Safe Mode — Core Daemon (Phase 1).
# → becomes:
"""Read the Room — Core Daemon.

# content_checker.py:2
"""Content filtering orchestrator for Spotify Family Safe Mode (Phase 2).
# → becomes:
"""Read the Room — Content filtering orchestrator.

# skip_client.py:2
"""Skip client abstractions for Spotify Family Safe Mode (Phase 2).
# → becomes:
"""Read the Room — Skip client abstractions.

# drug_scanner.py:2
"""Drug reference scanner for Spotify Family Safe Mode.
# → becomes:
"""Read the Room — Drug reference scanner.

# sexual_content_scanner.py:2
"""Sexual content scanner for Spotify Family Safe Mode.
# → becomes:
"""Read the Room — Sexual content scanner.

# web_ui/main.py:1
"""Spotify Family Safe Mode — Web UI Service (Phase 3).
# → becomes:
"""Read the Room — Web UI Service.

# web_ui/main.py:47
app = FastAPI(title="Spotify Family Safe Mode", docs_url=None, redoc_url=None)
# → becomes:
app = FastAPI(title="Read the Room", docs_url=None, redoc_url=None)

# lyrics_service.py:73
self._api = LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")
# → becomes:
self._api = LrcLibAPI(user_agent="ReadTheRoom/1.0")
```

### .env.example additions (following existing comment style)

```bash
# Docker user/group IDs — required so bind-mount files are owned by your user, not root.
# On Linux/macOS: export UID=$(id -u) && export GID=$(id -g) before running docker compose.
UID=1000
GID=1000

# Events log path — shared JSONL file written by daemon, read by web_ui.
# Both services must have this path accessible via their volume mounts.
EVENTS_PATH=data/events.jsonl
```

### Acceptance verification commands (grep-verifiable)

```bash
# HYG-01: .dockerignore exists and covers key items
cat .dockerignore | grep -E "^\.env$|^token_cache/"

# HYG-02: .claude/ no longer tracked
git ls-files .claude/  # must return empty

# HYG-03: No personal IP in test file
grep "192.168.1.164" tests/test_sonos_probe.py  # must return empty

# HYG-04: No old brand name in source files
grep -r "Spotify Family Safe Mode" daemon.py content_checker.py skip_client.py \
    drug_scanner.py sexual_content_scanner.py web_ui/main.py lyrics_service.py  # must return empty

# HYG-05: .env.example contains new vars
grep -E "^UID=|^GID=|^EVENTS_PATH=" .env.example  # must return 3 lines
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No .dockerignore | `.dockerignore` required for any COPY-all Dockerfile | Docker 1.x introduced it | Without it, `COPY . .` bakes secrets into image layers |
| Tracked dev tooling in git | Dev tooling (`.claude/`, `.planning/`) gitignored | Pre-publication standard | Prevents exposing personal absolute paths (530+ files in `.claude/`) |

**Deprecated/outdated:**
- Stale "(Phase N)" annotations in docstrings: drop entirely, per D-02.

## Open Questions

None — all decisions are locked. Phase is fully specified.

## Environment Availability

> Step 2.6: All operations are code/config edits plus a single git command. No external services required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | HYG-02 (`git rm --cached`) | Already in use (repo exists) | system | — |

**Missing dependencies with no fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (inferred from test files; no pyproject.toml yet — CI-02 in Phase 22) |
| Config file | none — `tests/conftest.py` adds project root to sys.path |
| Quick run command | `cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/test_sonos_probe.py -x -q` |
| Full suite command | `cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYG-01 | `.dockerignore` present and excludes `.env`, `token_cache/` | smoke (grep) | `grep -E "^\.env$" .dockerignore && grep "token_cache" .dockerignore` | ❌ Wave 0 (verification grep, no test file needed) |
| HYG-02 | `.claude/` absent from `git ls-files` output | smoke (git) | `[ -z "$(git ls-files .claude/)" ]` | ❌ Wave 0 (shell assertion, no test file needed) |
| HYG-03 | No `192.168.1.164` in `tests/test_sonos_probe.py`; existing probe tests still pass | unit | `python -m pytest tests/test_sonos_probe.py -x -q` | ✅ (file exists, tests use placeholder IP after edit) |
| HYG-04 | No "Spotify Family Safe Mode" in source; user-agent and FastAPI title updated | smoke (grep) | `grep -r "Spotify Family Safe Mode" daemon.py content_checker.py skip_client.py drug_scanner.py sexual_content_scanner.py web_ui/main.py lyrics_service.py` (must return empty) | ❌ Wave 0 (grep assertion) |
| HYG-05 | `.env.example` contains `UID`, `GID`, `EVENTS_PATH` entries | smoke (grep) | `grep -cE "^UID=|^GID=|^EVENTS_PATH=" .env.example` (must return 3) | ❌ Wave 0 (grep assertion) |

### Sampling Rate

- **Per task commit:** Run the requirement-specific grep or `pytest tests/test_sonos_probe.py -x -q` for HYG-03.
- **Per wave merge:** `python -m pytest tests/ -x -q` — full suite, confirms HYG-03 edit did not break probe tests.
- **Phase gate:** All five acceptance greps return clean before `/gsd:verify-work`.

### Wave 0 Gaps

All HYG verifications use grep assertions rather than pytest test files — no new test files are needed. The existing `tests/test_sonos_probe.py` covers HYG-03 behavioral verification after the IP replacement.

None — existing test infrastructure covers all phase requirements. Grep-based acceptance criteria are specified in the "Acceptance verification commands" code example above.

## Sources

### Primary (HIGH confidence)
- Direct source file inspection — `daemon.py`, `content_checker.py`, `skip_client.py`, `drug_scanner.py`, `sexual_content_scanner.py`, `web_ui/main.py`, `lyrics_service.py`, `tests/test_sonos_probe.py`
- Direct config inspection — `.env.example`, `.gitignore`, `docker-compose.yml`, `Dockerfile`, `web_ui/Dockerfile`
- `git ls-files .claude/` — 217 tracked files confirmed

### Secondary (MEDIUM confidence)
- Docker `.dockerignore` semantics: standard documented Docker behavior (applies to build context for the `context:` directory specified in `docker-compose.yml`)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all tooling already present
- Architecture: HIGH — all decisions locked in CONTEXT.md; source files directly inspected
- Pitfalls: HIGH — discovered from direct grep audit of actual file content

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable — no external dependencies)
