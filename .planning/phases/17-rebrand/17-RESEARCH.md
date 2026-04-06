# Phase 17: Rebrand - Research

**Researched:** 2026-04-05
**Domain:** String replacement in HTML template and README
**Confidence:** HIGH

## Summary

Phase 17 is a display-name-only rebrand. The old name "Spotify Family Safe Mode" (and its short form "Family Safe Mode") must be replaced with "Read the Room" in exactly two user-facing files: `web_ui/templates/index.html` and `README.md`. No source files are renamed. No Python logic changes.

The audit below identifies every occurrence of the old name across the codebase and classifies each as in-scope (user-visible display string) or out-of-scope (source code comments, Python module docstrings, internal config, planning documents). The planner needs only act on the in-scope items.

**Primary recommendation:** Edit exactly two files — `web_ui/templates/index.html` (three string changes) and `README.md` (two string changes). Everything else is out of scope for this phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RBR-01 | Dashboard `<title>` tag and visible app heading display "Read the Room" | index.html line 6 (`<title>`) and line 436 (`<h1>`) identified — both in scope |
| RBR-02 | README.md header and introduction updated to "Read the Room" | README.md line 1 (H1) and line 3 (intro sentence) identified — both in scope |
</phase_requirements>

## String Inventory

### In-Scope: User-Visible Display Strings

These are the only changes required to satisfy RBR-01 and RBR-02.

#### `web_ui/templates/index.html`

| Line | Current Value | Required Value | Requirement |
|------|---------------|----------------|-------------|
| 6 | `<title>Family Safe Mode</title>` | `<title>Read the Room</title>` | RBR-01 |
| 436 | `<h1>Spotify Family Safe Mode</h1>` | `<h1>Read the Room</h1>` | RBR-01 |
| 492 | `...when Family Safe Mode is on.` | `...when Read the Room is on.` | RBR-01 (incidental body copy) |

**Note on line 492:** The `<span class="empty-body">` text reads "Skips will appear here in real-time when Family Safe Mode is on." This is user-visible body copy in the Incident Log card's empty state. It contains the old brand name and should be updated. It is not explicitly called out in RBR-01's success criteria (which only names title + heading), but leaving a different old-name instance in the same file would be inconsistent. The planner should decide whether to include this; including it is the lower-risk choice.

#### `README.md`

| Line | Current Value | Required Value | Requirement |
|------|---------------|----------------|-------------|
| 1 | `# Spotify Family Safe Mode` | `# Read the Room` | RBR-02 |
| 3 | `Automatically skips explicit songs when Family Safe Mode is on...` | Update inline reference | RBR-02 |

**Line 3 detail:** The full sentence is: "Automatically skips explicit songs when Family Safe Mode is on. Polls Spotify playback, checks lyrics, and skips via Sonos or the Spotify API." The phrase "Family Safe Mode" here refers to the product feature toggle, not the app name. Replacing "Family Safe Mode" with "Read the Room" keeps it coherent: "Automatically skips explicit songs when Read the Room is on."

### Out-of-Scope: Source Code Strings (Do Not Touch)

These contain the old name but are NOT user-visible UI display strings. Changing them is deferred to RBR-03 (v2 source file rename).

| File | Line | Type | Reason Out of Scope |
|------|------|------|---------------------|
| `web_ui/main.py` | 1 | Module docstring | Source code comment, not rendered to user |
| `web_ui/main.py` | 46 | `FastAPI(title=...)` | OpenAPI title — `docs_url=None`, `redoc_url=None`, so Swagger UI is disabled. This string is never shown to users. |
| `daemon.py` | 2 | Module docstring | Source code comment |
| `content_checker.py` | (various) | Source code | Python source — file rename deferred |
| `sexual_content_scanner.py` | (various) | Source code | Python source — file rename deferred |
| `drug_scanner.py` | (various) | Source code | Python source — file rename deferred |
| `skip_client.py` | (various) | Source code | Python source — file rename deferred |
| `Makefile` | 35, 38, 41, 44 | Make targets | Developer CLI output, not user-facing dashboard |
| `.planning/**` | many | Planning docs | Internal docs, not user-facing |

### Confidence: HIGH — all occurrences verified by direct file read with line numbers.

## Architecture Patterns

This phase requires no new architecture. The pattern is:

1. Open file
2. Find exact string (as verified in the inventory above)
3. Replace with new string
4. Save

No template engine changes, no Python logic changes, no API changes, no CSS changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding all occurrences | Custom search script | Direct edit with known line numbers | Line numbers already confirmed; scripting adds risk of missed edge cases |

## Common Pitfalls

### Pitfall 1: Partial Brand Name Left in Body Copy
**What goes wrong:** RBR-01 success criteria mention title + heading, but line 492 in index.html has the old name in body copy. If only lines 6 and 436 are changed, "Family Safe Mode" still appears in the Incident Log empty state.
**Why it happens:** Success criteria list the primary visible locations; incidental body copy is easy to overlook.
**How to avoid:** Change all three index.html occurrences (lines 6, 436, 492) in the same edit.
**Warning signs:** Grep for "Family Safe Mode" in index.html after the edit — should return zero matches.

### Pitfall 2: README Line 3 Partial Update
**What goes wrong:** README H1 changed but intro sentence on line 3 still says "Family Safe Mode."
**Why it happens:** Two separate occurrences on adjacent lines; editor may find the H1 first and stop.
**How to avoid:** Update both line 1 and line 3 together.
**Warning signs:** Grep README.md for "Family Safe Mode" after edit — should return zero matches.

### Pitfall 3: Touching Out-of-Scope Python Files
**What goes wrong:** Overzealous find-replace touches module docstrings, FastAPI title, or source comments.
**Why it happens:** "Replace all in project" commands don't distinguish display strings from code.
**How to avoid:** Edit only the two in-scope files. Do not run project-wide replace.

## Runtime State Inventory

This is a display-name rename, not a data model or key rename. The string "Family Safe Mode" / "Spotify Family Safe Mode" does not appear in:

| Category | Finding |
|----------|---------|
| Stored data | None — state.json uses boolean key `family_safe_mode` (a code identifier, not a display name). No rename needed. |
| Live service config | None — no external service stores the display name as a config value. |
| OS-registered state | None verified — no Task Scheduler, pm2, or systemd unit names reference the display name. |
| Secrets/env vars | None — .env keys are identifiers (SPOTIFY_CLIENT_ID, etc.), not display names. |
| Build artifacts | None — Docker image tags in docker-compose.yml are `daemon` and `web_ui`, not the display name. |

**Conclusion:** This is a pure text-file edit. No data migration, no service restart required beyond normal container rebuild if running live.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | No automated test suite detected in project |
| Config file | None |
| Quick run command | Manual browser check |
| Full suite command | N/A |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RBR-01 | Browser tab title shows "Read the Room" | manual | N/A — visual check in browser | N/A |
| RBR-01 | Dashboard `<h1>` shows "Read the Room" | grep | `grep -n "Read the Room" web_ui/templates/index.html` | N/A |
| RBR-01 | Old name absent from index.html | grep | `grep -c "Family Safe Mode" web_ui/templates/index.html` must return 0 | N/A |
| RBR-02 | README H1 shows "Read the Room" | grep | `grep -n "Read the Room" README.md` | N/A |
| RBR-02 | Old name absent from README | grep | `grep -c "Family Safe Mode" README.md` must return 0 | N/A |

### Wave 0 Gaps
None — no test infrastructure needed. Verification is grep-based and manual browser check.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — this is a pure text-file edit with no build step required).

## Sources

### Primary (HIGH confidence)
- Direct file read of `web_ui/templates/index.html` — all occurrences identified with line numbers
- Direct file read of `README.md` — all occurrences identified with line numbers
- Direct file read of `web_ui/main.py` — confirmed `docs_url=None` makes FastAPI title non-user-facing
- Direct file read of `.planning/REQUIREMENTS.md` — RBR-01, RBR-02 scope confirmed
- Direct file read of `.planning/STATE.md` — confirmed "display-name only" decision

## Metadata

**Confidence breakdown:**
- String inventory: HIGH — verified by direct file reads with line numbers
- Scope boundary: HIGH — confirmed by REQUIREMENTS.md Out of Scope table and STATE.md decisions
- Pitfalls: HIGH — derived from direct observation of file contents

**Research date:** 2026-04-05
**Valid until:** Stable — only invalidated if index.html or README.md are edited before Phase 17 executes
