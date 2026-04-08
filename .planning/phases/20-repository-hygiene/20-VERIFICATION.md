---
phase: 20-repository-hygiene
verified: 2026-04-08T22:27:15Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Push to a public GitHub repo (or dry-run with git push --dry-run) and confirm .planning/ tracked files do not expose personal data to the public index"
    expected: "Either (a) .planning/ is untracked before push, or (b) the tracked .planning/ files are audited and acceptable for public view"
    why_human: ".planning/ is in .gitignore but 321 files remain in the git index. Git ignores only prevent NEW tracking — already-tracked files must be explicitly removed with git rm --cached. The plan explicitly deferred .planning/ untracking as out of scope, but the phase goal is 'safe to make public'. A human must decide: run git rm --cached -r .planning/ before first push, or accept that planning docs (including PROJECT.md with 192.168.1.164 and 66 files with absolute path /home/cgallarno/) will be publicly visible."
---

# Phase 20: Repository Hygiene Verification Report

**Phase Goal:** The repository is safe and non-embarrassing to make public — no credential exposure vectors, no personal data, no stale branding
**Verified:** 2026-04-08T22:27:15Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                         | Status     | Evidence                                                                        |
| --- | --------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------- |
| 1   | A Docker build cannot bake .env or token_cache/ into the image                               | VERIFIED   | .dockerignore exists; `grep -E "^\.env$"` and `grep "token_cache/"` both match |
| 2   | .claude/ directory is absent from git ls-files output                                        | VERIFIED   | `git ls-files .claude/` returns 0 files                                         |
| 3   | .claude/ is listed in .gitignore                                                              | VERIFIED   | `grep "^\.claude/$" .gitignore` matches                                         |
| 4   | No personal IP address (192.168.1.164) appears in tests/test_sonos_probe.py                  | VERIFIED   | `grep "192.168.1.164" tests/test_sonos_probe.py` returns 0 matches; 7 occurrences of 192.168.1.100 confirmed |
| 5   | No module docstring, FastAPI title, or user-agent string references "Spotify Family Safe Mode" | VERIFIED   | `grep -r "Spotify Family Safe Mode"` across all 7 source files returns no matches |
| 6   | .env.example documents UID, GID, and EVENTS_PATH with explanatory comments                   | VERIFIED   | `grep -cE "^UID=|^GID=|^EVENTS_PATH=" .env.example` returns 3; bind-mount comment and `id -u` export command both present |

**Score:** 6/6 truths verified (all plan must_haves pass)

**Residual finding (not in must_haves):** 321 `.planning/` files remain tracked in the git index despite `.planning/` being added to `.gitignore`. Of these, 17 contain the personal IP `192.168.1.164` (including `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md`) and 66 contain the absolute home path `/home/cgallarno/`. The Plan 01 summary explicitly acknowledged this as out of scope: "`.planning/` untracking is separate scope if needed." The phase goal of "safe to make public" is partially incomplete for this reason — flagged for human decision.

### Required Artifacts

| Artifact                      | Expected                                          | Status     | Details                                                                 |
| ----------------------------- | ------------------------------------------------- | ---------- | ----------------------------------------------------------------------- |
| `.dockerignore`               | Docker build context exclusions, contains `.env`  | VERIFIED   | Exists at repo root; contains .env, token_cache/, .claude/, tests/, .planning/, .git/ |
| `.gitignore`                  | Git ignore rules including .claude/               | VERIFIED   | Contains `.claude/` and `.planning/` under "Dev tooling" section        |
| `tests/test_sonos_probe.py`   | Anonymized IP; contains 192.168.1.100             | VERIFIED   | 7 occurrences of 192.168.1.100; 0 occurrences of 192.168.1.164         |
| `daemon.py`                   | Updated module docstring; contains "Read the Room — Core Daemon" | VERIFIED   | Line 2: `"""Read the Room — Core Daemon.`                              |
| `content_checker.py`          | Updated docstring                                 | VERIFIED   | Line 2: `"""Read the Room — Content filtering orchestrator.`            |
| `skip_client.py`              | Updated docstring                                 | VERIFIED   | Line 2: `"""Read the Room — Skip client abstractions.`                  |
| `drug_scanner.py`             | Updated docstring                                 | VERIFIED   | Line 2: `"""Read the Room — Drug reference scanner.`                   |
| `sexual_content_scanner.py`   | Updated docstring                                 | VERIFIED   | Line 2: `"""Read the Room — Sexual content scanner.`                   |
| `web_ui/main.py`              | Updated docstring and FastAPI title               | VERIFIED   | Docstring: `"""Read the Room — Web UI Service.`; `FastAPI(title="Read the Room", ...)` |
| `lyrics_service.py`           | Updated user-agent string                        | VERIFIED   | `LrcLibAPI(user_agent="ReadTheRoom/1.0")`                              |
| `.env.example`                | Documents UID, GID, EVENTS_PATH                  | VERIFIED   | UID=1000, GID=1000, EVENTS_PATH=data/events.jsonl with Docker-focused comments |

### Key Link Verification

| From                      | To                          | Via                          | Status   | Details                                                              |
| ------------------------- | --------------------------- | ---------------------------- | -------- | -------------------------------------------------------------------- |
| `.dockerignore`           | Dockerfile COPY . .         | Docker build context filter  | VERIFIED | Pattern `^\.env$` present; token_cache/, .claude/ all present        |
| `.gitignore`              | git index                   | git rm --cached -r .claude/  | VERIFIED | `git ls-files .claude/` = 0; `.claude/` line in .gitignore confirmed |
| `tests/test_sonos_probe.py` | probe_sonos_speakers in daemon.py | pytest test imports   | VERIFIED | Pattern `192.168.1.100` present (7 occurrences); 0 occurrences of personal IP |
| `web_ui/main.py`          | FastAPI app                 | FastAPI(title=...)           | VERIFIED | `FastAPI(title="Read the Room", docs_url=None, redoc_url=None)` confirmed |

### Data-Flow Trace (Level 4)

Not applicable — this phase performs file manipulation (gitignore, dockerignore, string substitution). No dynamic data rendering artifacts.

### Behavioral Spot-Checks

| Behavior                                   | Command                                                                     | Result | Status |
| ------------------------------------------ | --------------------------------------------------------------------------- | ------ | ------ |
| .dockerignore blocks .env at build context | `grep -E "^\.env$" .dockerignore`                                           | `.env` | PASS   |
| .claude/ fully untracked from git index    | `git ls-files .claude/ \| wc -l`                                            | `0`    | PASS   |
| Personal IP absent from test file          | `grep -c "192.168.1.164" tests/test_sonos_probe.py`                         | `0`    | PASS   |
| Replacement IP count correct               | `grep -c "192.168.1.100" tests/test_sonos_probe.py`                         | `7`    | PASS   |
| All "Spotify Family Safe Mode" strings gone | `grep -r "Spotify Family Safe Mode" daemon.py content_checker.py ...`      | (empty) | PASS  |
| .env.example new vars count                | `grep -cE "^UID=\|^GID=\|^EVENTS_PATH=" .env.example`                      | `3`    | PASS   |
| D-04 boundary: family_safe_mode preserved  | `grep -c "family_safe_mode" web_ui/main.py`                                 | `9`    | PASS   |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                         | Status    | Evidence                                                    |
| ----------- | ----------- | --------------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------- |
| HYG-01      | 20-01       | .dockerignore exists; OAuth tokens, .env, and runtime data dirs excluded from Docker build context | SATISFIED | .dockerignore at repo root; .env and token_cache/ confirmed |
| HYG-02      | 20-01       | .claude/ untracked from git and added to .gitignore                                                | SATISFIED | git ls-files .claude/ = 0; .claude/ in .gitignore          |
| HYG-03      | 20-02       | Personal IP 192.168.1.164 replaced with 192.168.1.100 in tests/test_sonos_probe.py                | SATISFIED | 0 matches for old IP; 7 matches for new IP                  |
| HYG-04      | 20-02       | "Spotify Family Safe Mode" replaced with "Read the Room" in all module docstrings and source strings | SATISFIED | grep across 7 files returns empty; all "Read the Room" strings confirmed |
| HYG-05      | 20-02       | .env.example updated with UID, GID, and EVENTS_PATH with explanatory comments                     | SATISFIED | 3 vars present; bind-mount comment and `id -u` export both confirmed |

No orphaned requirements: REQUIREMENTS.md maps exactly HYG-01 through HYG-05 to Phase 20, all five claimed by the two plans.

### Anti-Patterns Found

| File                         | Line | Pattern                               | Severity | Impact                                               |
| ---------------------------- | ---- | ------------------------------------- | -------- | ---------------------------------------------------- |
| `.planning/PROJECT.md`       | 79   | `192.168.1.164` (personal home IP)    | WARNING  | File is tracked in git index; would be public on push |
| `.planning/REQUIREMENTS.md`  | HYG-03 row | `192.168.1.164` (in requirements description) | WARNING | File is tracked; would be public on push      |
| 66 `.planning/**` files      | various | `/home/cgallarno/` absolute path    | WARNING  | Personal username in 66 tracked planning files       |

**Classification:** These are WARNING-level, not blockers for the must_haves. The personal data exists only in `.planning/` files, which the phase's Plan 01 summary explicitly acknowledged as out of scope ("`.planning/` untracking is separate scope if needed"). The `.planning/` directory is gitignored to prevent future additions from being tracked, but `git rm --cached -r .planning/` was not run, so all 321 pre-existing files remain in the git index. A `git push` to a public remote would expose this content.

### Human Verification Required

#### 1. Decide and Execute .planning/ Untracking Before Public Push

**Test:** Before pushing to a public repository, evaluate whether `.planning/` content is acceptable for public view.

**Expected:** Either run `git rm --cached -r .planning/` to remove all 321 planning files from the git index (they remain on disk, gitignore prevents re-tracking), or conduct a targeted audit and accept the planning docs as public content.

**Why human:** The decision requires judgment: the planning docs contain the personal home IP `192.168.1.164` in context (e.g., PROJECT.md: "Music plays through Living Room Sonos (192.168.1.164)") and absolute paths (`/home/cgallarno/`) in 66 files. The phase goal explicitly requires "no personal data." Whether this constitutes an embarrassing data exposure is a human call. The mechanical fix is a single `git rm --cached -r .planning/` command, but it must be intentional and committed.

**Files involved:**
- `.planning/PROJECT.md` — contains `192.168.1.164`
- `.planning/REQUIREMENTS.md` — contains `192.168.1.164` in HYG-03 description
- 17 tracked `.planning/**` files containing `192.168.1.164`
- 66 tracked `.planning/**` files containing `/home/cgallarno/`

### Gaps Summary

All five HYG requirements are satisfied. All plan must_haves pass at all verification levels (exists, substantive, wired). No source files or committed artifacts contain personal data.

The sole unresolved item is a pre-existing condition that the plan explicitly chose not to address: 321 `.planning/` files remain in the git index. The plan added `.planning/` to `.gitignore` (which prevents new tracking) but did not run `git rm --cached -r .planning/` to untrack the existing files. The Plan 01 summary acknowledged this gap: "`.planning/` untracking is separate scope if needed."

This is not a gap against the must_haves but is a gap against the phase goal ("safe to make public — no personal data"), since `.planning/PROJECT.md` and others contain the real home IP and absolute personal paths. A human must decide whether to run `git rm --cached -r .planning/` before the first public push.

---

_Verified: 2026-04-08T22:27:15Z_
_Verifier: Claude (gsd-verifier)_
