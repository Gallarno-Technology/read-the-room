# Phase 6: Daemon SSE Extensions - Research

**Researched:** 2026-04-02
**Domain:** Python daemon instrumentation — event emission, file I/O, poll loop surgery
**Confidence:** HIGH

## Summary

Phase 6 is pure daemon instrumentation with no new dependencies and no external integration points. The entire implementation lives in `daemon.py` (primary), `web_ui/main.py` (env var rename propagation), and `docker-compose.yml` (env var rename). All design decisions are locked in CONTEXT.md — the planner has no architecture choices to make, only sequencing choices.

The work breaks into three self-contained surgical changes: (1) rename `_append_skip_event()` to `_append_event()` and update its `SKIP_EVENTS_PATH` reference to use a new `EVENTS_PATH` constant, (2) insert `track_change` and `eval_result` event emissions in `poll_loop()` at precise locations relative to the existing FSM branch, and (3) add `_write_now_playing()` to write `data/now_playing.json`. The env var rename propagates to `web_ui/main.py` and `docker-compose.yml` as a mechanical find-and-replace.

**Primary recommendation:** Plan three sequential tasks — (A) rename + env var migration, (B) event emission in poll_loop with eval_state mapping, (C) now_playing.json write. Test each task with a dedicated unit test before moving on.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rename `data/skip_events.jsonl` → `data/events.jsonl`. All daemon events (skip, five_skip_warning, track_change, eval_result) write to this single file. Update `SKIP_EVENTS_PATH` env var name to `EVENTS_PATH` in daemon.py, web_ui/main.py, and docker-compose.yml. web_ui tails this file; browser routes by `type` field.

- **D-02:** Canonical `eval_state` strings are kebab-case. The complete state machine:
  - `"evaluating"` — track detected, ContentChecker not yet complete
  - `"passed"` — track checked, no issues found
  - `"no-lyrics"` — LRCLIB returned nothing and explicit flag was clear (no skip)
  - `"skipped"` — track was auto-skipped by the daemon
  - `"paused"` — 5th consecutive skip; playback was paused instead of skipped
  - `"fsm-off"` — FSM was disabled; evaluation did not run

- **D-03:** The daemon always emits `track_change` and `eval_result` events regardless of FSM state. When FSM is off, `eval_result` fires with `eval_state: "fsm-off"`. Same event schema, same file — no special code path. now_playing.json is also written in both FSM-on and FSM-off cases.

- **D-04:** `track_change` event schema (emitted before ContentChecker runs):
  ```json
  {
    "type": "track_change",
    "track_id": "<spotify_track_id>",
    "track": "<track_name>",
    "artist": "<artist_name>",
    "album_art_url": "<url_of_640px_image_or_null>",
    "eval_state": "evaluating",
    "timestamp": "<HH:MM:SS>"
  }
  ```

- **D-05:** `eval_result` event schema (emitted after ContentChecker completes, or immediately when FSM is off):
  ```json
  {
    "type": "eval_result",
    "track_id": "<spotify_track_id>",
    "eval_state": "<passed|no-lyrics|skipped|paused|fsm-off>",
    "timestamp": "<HH:MM:SS>"
  }
  ```

- **D-06:** `now_playing.json` schema (overwritten on each track_change, then again after eval_result):
  ```json
  {
    "track_id": "<spotify_track_id>",
    "track": "<track_name>",
    "artist": "<artist_name>",
    "album_art_url": "<url_or_null>",
    "eval_state": "<evaluating|passed|no-lyrics|skipped|paused|fsm-off>",
    "timestamp": "<ISO-8601>"
  }
  ```
  Written to `data/now_playing.json`. Shared volume with web_ui container.

- **D-07:** Album art URL: use the 640×640 image from `track["album"]["images"]` (index 0 after Spotify returns images sorted largest-first). Set to `null` if images list is empty.

### Claude's Discretion

- Where exactly in the poll_loop to slot the new `_append_event()` calls (before/after existing skip logic)
- Whether to inline `eval_state` mapping or extract a small helper function
- Exact env var migration approach (backwards-compat alias vs hard rename)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DAEM-01 | Daemon emits a `track_change` event on the SSE channel immediately when a new track is detected, before evaluation runs | D-04 defines schema; insert before `content_checker.check()` call in poll_loop at line ~199 |
| DAEM-02 | Daemon emits an `eval_result` event for every track after evaluation completes, regardless of outcome (passed, no-lyrics, or skipped) | D-05 defines schema; four code paths in poll_loop must all emit (skip, five_skip_warning path, allow, and FSM-off); eval_state mapping from (action, reason) documented below |
| DAEM-03 | Daemon writes current track metadata and evaluation state to `now_playing.json` after each evaluation | D-06 defines schema; write twice per track: once at "evaluating", once after eval completes; uses same direct-write pattern as `_append_event()` |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies — everything already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | — | Serialize event dicts to JSONL lines | Already used in `_append_skip_event()` |
| Python stdlib `os` | — | `makedirs`, `path.dirname` for `data/` dir creation | Already used in `_append_skip_event()` |
| Python stdlib `time` | — | `time.strftime("%H:%M:%S")` for event timestamps | Existing pattern in all skip/warning events |
| Python stdlib `datetime` | — | `datetime.utcnow().isoformat()` for ISO-8601 `now_playing.json` timestamp | New — needed for D-06 timestamp format difference |

No `pip install` required. Phase 6 adds no new packages.

**Timestamp format note (HIGH confidence):** `now_playing.json` uses ISO-8601 (D-06) while events.jsonl uses `HH:MM:SS` (D-04, D-05). These are different and intentional. Use `datetime.datetime.utcnow().isoformat() + "Z"` for now_playing.json, `time.strftime("%H:%M:%S")` for event lines.

## Architecture Patterns

### Recommended Change Sequence

The three surgical changes should be applied in dependency order:

```
Task A: Rename + env var migration
  daemon.py:
    SKIP_EVENTS_PATH  →  EVENTS_PATH
    default "data/skip_events.jsonl"  →  "data/events.jsonl"
    _append_skip_event()  →  _append_event()
    all 3 call sites updated
  web_ui/main.py:
    SKIP_EVENTS_PATH  →  EVENTS_PATH
    default "data/skip_events.jsonl"  →  "data/events.jsonl"
  docker-compose.yml:
    SKIP_EVENTS_PATH env var  →  EVENTS_PATH

Task B: Event emission in poll_loop
  Emit track_change before content_checker.check() (DAEM-01)
  Emit eval_result after each code path (DAEM-02)
  Extract _eval_state_from_result() helper (Claude's discretion)

Task C: now_playing.json writer
  Add _write_now_playing(track_data: dict) helper
  Call it twice per track cycle: at "evaluating", after eval_result
```

### Pattern 1: Event emission placement in poll_loop

The existing `poll_loop` has this shape after line 166 (`if track_id != state.get("last_track_id")`):

```python
# [NEW] emit track_change HERE — before any FSM check
_append_event({...})
_write_now_playing({..., "eval_state": "evaluating", ...})

# existing: save_state, load_state, FSM transition reset

if state.get("family_safe_mode", False):
    # existing device checks
    action, reason, severity = await content_checker.check(track)

    if action == "allow":
        consecutive_skips = 0
        # [NEW] emit eval_result with mapped eval_state (passed or no-lyrics)

    if action == "skip":
        if consecutive_skips + 1 >= 5:
            # existing pause + five_skip_warning event
            # [NEW] emit eval_result with eval_state: "paused"
        else:
            success = await client.skip(...)
            if success:
                # existing skip event
                # [NEW] emit eval_result with eval_state: "skipped"
            # (skip failure: no eval_result — skip failed, no state change)
else:
    # FSM off
    # [NEW] emit eval_result with eval_state: "fsm-off"
```

**Critical ordering rule (HIGH confidence, verified from CONTEXT.md):** `track_change` fires unconditionally at the top of the `if track_id != state.get("last_track_id")` block, before the FSM branch. `eval_result` fires inside each branch outcome.

### Pattern 2: eval_state mapping from (action, reason)

`ContentChecker.check()` returns `(action, reason, severity)`. The mapping to `eval_state` (D-02):

| action | reason | eval_state |
|--------|--------|------------|
| `"skip"` | `"explicit"` | `"skipped"` |
| `"skip"` | `"profanity"` | `"skipped"` |
| `"allow"` | `"clean"` | `"passed"` |
| `"allow"` | `"instrumental"` | `"passed"` |
| `"allow"` | `"lyrics_unavailable"` | `"no-lyrics"` |
| `"allow"` | `"no_lyrics_service"` | `"no-lyrics"` |
| five_skip pause path | — | `"paused"` |
| FSM off | — | `"fsm-off"` |

**Note on "no-lyrics" (MEDIUM confidence):** The CONTEXT.md definition says `"no-lyrics"` applies when "LRCLIB returned nothing and explicit flag was clear (no skip)". In `ContentChecker.check()`, both `"lyrics_unavailable"` and `"no_lyrics_service"` reasons result in `action="allow"` with no skip. Both should map to `"no-lyrics"`.

**Note on skip failure:** If `client.skip()` returns `False`, no skip event is emitted today and no `eval_result` should be emitted either — the track remains at whatever was playing. The plan should make this explicit (no eval_result on skip failure).

### Pattern 3: `_write_now_playing()` helper

Direct-write pattern (not atomic rename — EBUSY on bind-mounted files, same constraint as `save_state()` and `_append_event()`):

```python
NOW_PLAYING_PATH = os.path.join(os.path.dirname(EVENTS_PATH), "now_playing.json")

def _write_now_playing(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(NOW_PLAYING_PATH) or ".", exist_ok=True)
        with open(NOW_PLAYING_PATH, "w") as f:
            json.dump(data, f)
    except OSError as exc:
        log.error("[NOW_PLAYING] failed to write: %s", exc)
```

The `data/` directory is guaranteed to exist by the time `_write_now_playing()` is called because `_append_event()` always runs first (it calls `os.makedirs`). The `os.makedirs` guard in `_write_now_playing()` is still good defensive coding.

### Pattern 4: Album art URL extraction (D-07)

```python
images = track.get("album", {}).get("images", [])
album_art_url = images[0]["url"] if images else None
```

Spotify returns images sorted largest-first. Index 0 is the 640×640 image when available.

### Anti-Patterns to Avoid

- **Atomic file rename for now_playing.json:** `os.replace()` raises `EBUSY` on bind-mounted files on Linux (confirmed pattern from Phase 1 decisions). Use direct `open("w")` write.
- **Emitting eval_result only on skip:** D-03 mandates eval_result fires for EVERY track including those that pass. This is the new behavior; the existing code only emits skip events.
- **Extending state.json for now_playing data:** D-06 locks `now_playing.json` as a separate file. Do not merge into `state.json`.
- **Adding a new env var for EVENTS_PATH:** Decision D-01 is a rename, not an addition. No backwards-compat alias — hard rename.
- **Forgetting the FSM-off branch:** The `else` branch of `if state.get("family_safe_mode", False)` currently has no event emission. Phase 6 adds `eval_result` with `eval_state: "fsm-off"` there.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom serializer | `json.dumps(event)` | Already used for all events; consistent |
| Directory creation | Manual mkdir logic | `os.makedirs(..., exist_ok=True)` | Already used in `_append_event()` |
| Timestamp formatting | Custom time logic | `time.strftime("%H:%M:%S")` for events, `datetime.utcnow().isoformat()` for now_playing | Established pattern |

**Key insight:** Phase 6 is a surgical instrumentation change. Every primitive needed already exists in the codebase. No new patterns, no new libraries.

## Common Pitfalls

### Pitfall 1: Mismatched timestamp formats between events.jsonl and now_playing.json
**What goes wrong:** `now_playing.json` uses ISO-8601 but events.jsonl uses `HH:MM:SS`. Using the wrong format in the wrong file breaks Phase 7's `GET /now-playing` parsing.
**Why it happens:** D-04/D-05 specify `HH:MM:SS`, D-06 specifies ISO-8601 — easy to miss the distinction.
**How to avoid:** `_write_now_playing()` always uses `datetime.datetime.utcnow().isoformat() + "Z"`. `_append_event()` always uses `time.strftime("%H:%M:%S")`.
**Warning signs:** now_playing.json has "14:22:05" instead of "2026-04-02T14:22:05Z".

### Pitfall 2: eval_result not emitted after skip failure
**What goes wrong:** The existing code has a `[SKIP_FAILED]` log path where `success=False`. If eval_result is emitted here, the UI could show "skipped" for a track that never actually skipped.
**Why it happens:** The eval_result emission loop needs to cover all success paths but not failure paths.
**How to avoid:** Only emit `eval_result: "skipped"` inside the `if success:` block. No eval_result on skip failure.
**Warning signs:** Tests show eval_result emitted even when mock skip returns False.

### Pitfall 3: track_change fires too early (before save_state)
**What goes wrong:** If `_append_event(track_change)` runs before `save_state({"last_track_id": track_id})`, a crash between those two lines could leave `last_track_id` un-persisted — daemon restarts and fires a duplicate track_change on the same track.
**Why it happens:** Ordering the new call at the very top of the block, before `save_state`.
**How to avoid:** Slot `track_change` emission after `save_state()` but before `content_checker.check()`. The events log is append-only; a duplicate line is more visible than a missed persist.
**Warning signs:** After daemon restart, a duplicate track_change appears for the same track_id.

### Pitfall 4: now_playing.json not written in FSM-off path
**What goes wrong:** D-03 says now_playing.json is written in both FSM-on and FSM-off cases. If the now_playing write is nested inside the FSM-on branch, it silently skips the write when FSM is off.
**Why it happens:** Copying the write call inside the `if state.get("family_safe_mode")` block.
**How to avoid:** The first `_write_now_playing()` call (evaluating state) lives outside any FSM branch. The second call (final state) must be inside each FSM branch AND inside the FSM-off else clause.
**Warning signs:** `data/now_playing.json` is absent or stale when FSM is toggled off.

### Pitfall 5: EVENTS_PATH constant computed before data/ dir exists
**What goes wrong:** `NOW_PLAYING_PATH` derived from `EVENTS_PATH` fails if `EVENTS_PATH` has no directory component.
**Why it happens:** Default value `"data/events.jsonl"` — `os.path.dirname` returns `"data"` correctly. But if someone sets `EVENTS_PATH=events.jsonl` (no dir), `dirname` returns `""` and `makedirs("")` raises.
**How to avoid:** `os.makedirs(os.path.dirname(NOW_PLAYING_PATH) or ".", exist_ok=True)` — the `or "."` guard already exists in `_append_event()`. Copy this pattern exactly.
**Warning signs:** `OSError: [Errno 2] No such file or directory: ''` in daemon logs.

## Code Examples

Verified patterns from existing codebase:

### Existing _append_event (to be renamed from _append_skip_event)
```python
# Source: daemon.py line 89-96
def _append_skip_event(event: dict) -> None:
    try:
        os.makedirs(os.path.dirname(SKIP_EVENTS_PATH) or ".", exist_ok=True)
        with open(SKIP_EVENTS_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as exc:
        log.error("[EVENTS] failed to write skip event log: %s", exc)
```

### Existing timestamp pattern
```python
# Source: daemon.py lines 228, 232, 254, 261 — used for all existing events
"timestamp": time.strftime("%H:%M:%S")
```

### Existing state read pattern after track change
```python
# Source: daemon.py line 176-177
save_state({"last_track_id": track_id})
state = load_state()   # re-read disk so family_safe_mode and future keys are fresh
```

### Album art extraction
```python
# Derived from D-07 + Spotify API structure
images = track.get("album", {}).get("images", [])
album_art_url = images[0]["url"] if images else None
```

### ContentChecker return tuple (for eval_state mapping)
```python
# Source: content_checker.py line 39
async def check(self, track: dict) -> tuple[str, str, int]:
    # returns (action, reason, severity)
    # action: "skip" | "allow"
    # reason: "explicit" | "profanity" | "instrumental" | "clean" |
    #         "lyrics_unavailable" | "no_lyrics_service"
```

## Runtime State Inventory

Phase 6 renames `data/skip_events.jsonl` → `data/events.jsonl`. This affects runtime state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/skip_events.jsonl` — existing event log on the host bind mount | File rename on host (or let daemon auto-create new file; old file is not read at startup — `_file_tail()` seeks to end) |
| Live service config | `docker-compose.yml` `SKIP_EVENTS_PATH` env var injected to both containers | Code edit in docker-compose.yml — update env var name and default |
| OS-registered state | None — no task scheduler, pm2, or systemd units reference the file path | None |
| Secrets/env vars | `.env` may contain `SKIP_EVENTS_PATH=data/skip_events.jsonl` if user customized it | Update `.env` if set; add migration note to README or plan |
| Build artifacts | None — no compiled artifacts reference the events file path | None |

**Migration strategy:** Because `_file_tail()` seeks to EOF on startup (skips history), the old file's content is not read after restart. The rename is safe to do as a hard cut: rename env var, restart containers, new file is created automatically by `_append_event()` on first event. The old `skip_events.jsonl` can remain on disk harmlessly — no code reads it after rename.

**User .env risk (LOW confidence):** If the user has `SKIP_EVENTS_PATH` set explicitly in `.env`, it will be ignored after the rename. The plan should include a step to check for and update this. Cannot verify without examining the user's `.env` file (not in repo).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | none (pytest discovers from tests/) |
| Quick run command | `.venv/bin/pytest tests/test_daemon_events.py -x -q` |
| Full suite command | `.venv/bin/pytest tests/ -q` |

### Current test suite status
- 16 passing, 2 failing (pre-existing failures in `test_skip_client.py` — soco mock issue unrelated to Phase 6)
- `tests/conftest.py` adds project root to sys.path — daemon.py importable

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DAEM-01 | `track_change` event written to events.jsonl before check() runs | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_track_change_emitted_before_check -x` | ❌ Wave 0 |
| DAEM-01 | `track_change` has `eval_state: "evaluating"` and all required fields | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_track_change_schema -x` | ❌ Wave 0 |
| DAEM-02 | `eval_result` emitted for allowed track (passed) | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_passed -x` | ❌ Wave 0 |
| DAEM-02 | `eval_result` emitted for skipped track | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_skipped -x` | ❌ Wave 0 |
| DAEM-02 | `eval_result` emitted with `fsm-off` when FSM disabled | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_fsm_off -x` | ❌ Wave 0 |
| DAEM-02 | `eval_result` NOT emitted on skip failure | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_not_emitted_on_skip_failure -x` | ❌ Wave 0 |
| DAEM-03 | `now_playing.json` written at "evaluating" on track change | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_now_playing_evaluating -x` | ❌ Wave 0 |
| DAEM-03 | `now_playing.json` overwritten with final state after eval | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_now_playing_final_state -x` | ❌ Wave 0 |
| D-01 | Existing skip/warning events still appear in events.jsonl | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_existing_events_unaffected -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_daemon_events.py -x -q`
- **Per wave merge:** `.venv/bin/pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_daemon_events.py` — covers all DAEM-01, DAEM-02, DAEM-03 requirements
- [ ] No new framework install needed (pytest + pytest-asyncio already installed)

**Testing approach note:** `daemon.py` functions (`_append_event`, `_write_now_playing`, `poll_loop`) can be unit-tested by mocking `open`, `os.makedirs`, the `sp` Spotify client, and `content_checker.check()`. The existing `tests/conftest.py` already adds the project root to `sys.path` making `daemon` importable. The `poll_loop` is an `async` function — tests will use `pytest.mark.asyncio`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | daemon.py execution | ✓ | 3.12 (.venv) | — |
| pytest + pytest-asyncio | Test execution | ✓ | pytest 9.0.2 | — |
| docker compose | Integration verification | Not checked | — | Manual file inspection |

**Note:** Phase 6 is code-only with no new external services. The `data/` bind mount already exists from Phase 3 (Gap-2 fix). No blocking dependencies.

## Open Questions

1. **User's .env file**
   - What we know: `.env` is not in the repo; it may contain `SKIP_EVENTS_PATH=data/skip_events.jsonl`
   - What's unclear: Whether the user customized this value
   - Recommendation: Plan includes a step checking for `SKIP_EVENTS_PATH` in `.env` and updating it if present; add a comment in the migration note

2. **eval_result on skip failure**
   - What we know: CONTEXT.md does not explicitly address what happens when `client.skip()` returns `False`
   - What's unclear: Should `eval_result` fire with `eval_state: "skipped"` anyway (reflecting intended action) or not fire (reflecting actual outcome)?
   - Recommendation: Do NOT emit eval_result on skip failure (actual outcome wins). The daemon logs `[SKIP_FAILED]` — the event feed should not claim the track was skipped if the skip failed. This is Claude's discretion.

3. **EVENTS_PATH env var backwards-compat**
   - What we know: Decision D-01 says "rename" not "add alias"
   - What's unclear: Whether any external monitoring/scripts depend on `SKIP_EVENTS_PATH`
   - Recommendation: Hard rename per D-01. Document in the plan as a breaking change for anyone with custom `.env`.

## Sources

### Primary (HIGH confidence)
- `daemon.py` — Direct code read; `poll_loop()`, `_append_skip_event()`, `SKIP_EVENTS_PATH` constant — full implementation verified
- `web_ui/main.py` — Direct code read; `SKIP_EVENTS_PATH`, `_file_tail()`, `_startup()` — full implementation verified
- `docker-compose.yml` — Direct code read; env var injections, volume mounts verified
- `content_checker.py` — Direct code read; return tuple `(action, reason, severity)` documented
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` — All design decisions (D-01 through D-07) locked

### Secondary (MEDIUM confidence)
- `tests/` directory — Test structure, pytest version, conftest.py pattern verified by direct read
- `.planning/REQUIREMENTS.md` — DAEM-01, DAEM-02, DAEM-03 requirement text verified

### Tertiary (LOW confidence)
- User `.env` customization risk — inferred from `.env` not being in repo; not directly verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already installed; verified by direct code read
- Architecture: HIGH — all decisions locked in CONTEXT.md; poll_loop structure fully read
- Pitfalls: HIGH — derived from direct code read of existing patterns and established constraints (EBUSY, direct-write)
- Test gaps: HIGH — tests/ directory listed and existing tests read; no test_daemon_events.py found

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable codebase, no external service dependencies)
