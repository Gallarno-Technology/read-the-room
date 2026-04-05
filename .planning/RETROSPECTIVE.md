# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-02
**Phases:** 3 | **Plans:** 14 | **LOC:** ~1,500 Python

### What Was Built

- Asyncio daemon polling Spotify every 1s — detects track changes, checks explicit flag, fetches lyrics from LRCLIB, scans for profanity with leet-speak handling
- Dual skip path: SoCo UPnP for Sonos speakers (`is_restricted=True`), Spotify Web API for everything else; fallback from SoCo to Spotify API on error 701
- FastAPI web UI with real-time SSE skip feed, FSM toggle, and 5-skip pause warning banner — served in Docker alongside the daemon
- File-based IPC (`skip_events.jsonl`) between daemon and web_ui containers — replaces broken cross-process asyncio.Queue
- `SONOS_SPEAKER_IPS` env var to bypass SSDP multicast discovery blocked by host firewall
- Group coordinator routing in SoCo (`_soco_next` / `_soco_pause`) — fixes UPnP error 701 when Sonos is in Spotify Connect mode

### What Worked

- **GSD coarse granularity** — 14 plans across 3 phases kept plans focused and parallelizable; no plan was too large to execute atomically
- **SkipClient ABC** — isolating skip logic behind an interface meant daemon.py never needed changing when SoCo edge cases were discovered; just add methods to the implementations
- **File-based IPC** — the simplest cross-container solution; no Redis, no broker, just a jsonl tail. Proven immediately reliable
- **`SONOS_SPEAKER_IPS` env var** — immediately unblocked Sonos testing without touching firewall config; fits naturally into Docker's env_file pattern
- **Debugging with notes + debug files** — capturing root causes in `.planning/debug/` during investigation saved re-diagnosing the same issue

### What Was Inefficient

- **Signal bot scope pivot** — Phase 3 was originally "Signal notifications + interactive confirmations"; Signal bot was cut mid-phase when the web dashboard proved simpler. A clearer v1 scoping discussion upfront would have saved planning overhead
- **In-process queue assumption** — the SSE queue was initially designed as an in-process asyncio.Queue; the Docker container boundary wasn't caught until integration. File-tail was the right design from the start given docker-compose
- **SSDP firewall issue discovered late** — Sonos discovery only failed at runtime; the host firewall blocking multicast wasn't caught in planning. A `SONOS_SPEAKER_IPS` escape hatch should have been in Phase 2 from day 1
- **`save_state()` read-merge** — the race between daemon writes and FSM toggle writes required adding a read-merge pattern mid-phase; this is a known pattern for any shared-file state and should be a default

### Patterns Established

- **SkipClient ABC** — all future transport integrations (Bridge, AirPlay, etc.) add a new class implementing the same `skip()` / `pause()` interface; daemon.py stays clean
- **File-based IPC with jsonl** — event logs as append-only jsonl files tailed by consumers; works across process and container boundaries; naturally persistent
- **read-merge-write for state.json** — any writer loads the current disk state, merges its fields, then writes; prevents clobbering unrelated keys
- **GSD debug notes** — whenever a non-obvious root cause is found, capture it in `.planning/debug/` before fixing; prevents re-investigation in future sessions
- **env var escape hatches for hardware** — any hardware discovery mechanism (Sonos SSDP, mDNS, etc.) should have a manual IP/address override env var from day 1

### Key Lessons

1. **Design for the Docker boundary from the start** — asyncio coroutines don't cross container walls; assume file or socket IPC for any multi-service architecture
2. **Hardware discovery is optional, not required** — always provide a manual override for any network discovery mechanism; discovery is an optimization, not a dependency
3. **Group coordinator routing is mandatory for Sonos groups** — any UPnP transport command must target the group coordinator, not an arbitrary group member; build this in, not as a hotfix
4. **Explicit flag + lyric scan is the right layered strategy** — fast path (explicit flag) handles the common case in zero network time; lyric scan catches the gaps; sentiment analysis is v2
5. **Phase scope creep signals a scope conversation, not a code fix** — when a phase's original goal (Signal bot) conflicts with a simpler alternative (web dashboard), pause and re-scope rather than building both

### Cost Observations

- Model mix: primarily Sonnet 4.6 (GSD balanced profile)
- Sessions: ~8 sessions over 2 days (2026-04-01 → 2026-04-02)
- Notable: coarse granularity (14 plans / 3 phases) kept each session focused; no context overflow events

---

## Milestone: v1.1 — Deployment

**Shipped:** 2026-04-02
**Phases:** 2 | **Plans:** 4 | **LOC:** +~713 lines (Python + YAML + docs)

### What Was Built

- `probe_sonos_speakers()` as first-class startup step in `daemon.py` — SSDP auto-discovery with actionable multicast failure warnings (firewall/bridge hints) in `skip_client.py`
- `SONOS_SPEAKER_IPS` reframed from workaround to documented escape hatch (`Name=IP,...` format) in `.env.example`
- Docker healthcheck: `poll_loop()` touches `/app/.healthcheck` every cycle; `docker-compose.yml` detects 90s hang (interval 30s × retries 3) and triggers auto-restart
- `README.md`: 7-step Quick Start with OAuth flow, UID/GID pitfall, `systemctl enable docker` boot persistence
- `PROXMOX.md`: LXC SSDP multicast context + `SONOS_SPEAKER_IPS` bypass for restricted networks; no specific firewall commands (links to official docs)
- TDD scaffold first (RED) → implementation (GREEN) for both discovery and healthcheck — pytest + pytest-asyncio added to requirements

### What Worked

- **TDD RED/GREEN discipline** — writing failing tests first for `probe_sonos_speakers` and healthcheck made the behavioral contracts explicit before any wiring; caught edge cases (stale file, coordinator-only probe) that inline implementation would have missed
- **Touch-file healthcheck simplicity** — cross-language, zero dependencies, detects the exact failure mode (hung event loop, process alive); no custom HTTP health endpoint needed
- **PROXMOX.md as a separate file** — isolating the LXC multicast edge case kept README minimal; developers who don't need it never see it
- **3-section README constraint** — forcing Quick Start / Prerequisites / Updating only prevented scope creep into troubleshooting and reference docs; README stayed actionable

### What Was Inefficient

- **pytest not in requirements.txt** — the image didn't have pytest installed; `docker compose run --rm daemon python -m pytest` failed on first try. Any test infrastructure should be verified in the container at the end of the first test-writing task
- **Container name typo in UAT** — healthcheck UAT described `docker exec <container>` without the exact container name; user hit a typo-based error. UAT tests with CLI commands should include the exact container name from `docker ps`

### Patterns Established

- **TDD for daemon behaviors** — new daemon.py behaviors (polling, probing, touching files) get a `tests/test_*.py` file with RED tests before implementation; `docker compose run --rm daemon python -m pytest` is the verification step
- **Escape hatch env var = documented at birth** — every hardware/network discovery mechanism ships with a manual override in `.env.example` on day 1, with a comment explaining when to use it
- **Separate edge-case docs** — niche deployment scenarios (Proxmox/LXC, VPN, unusual networks) go in dedicated `.md` files linked from README via blockquote, not inline

### Key Lessons

1. **pytest must be in the image** — add test runner dependencies to `requirements.txt` before writing any test; don't assume the dev environment matches the container
2. **Healthcheck probe = mtime check on a touched file** — simpler than HTTP, works for any polling daemon, catches hung event loops that HTTP endpoints would miss
3. **Minimal README sections > comprehensive README** — 3 sections (Quick Start, Prerequisites, Updating) forces the author to make the happy path work without workarounds; troubleshooting sections invite workarounds instead of fixes
4. **SSDP is primary, IP override is escape hatch** — the default should always be discovery; manual overrides should be labeled as such in all docs

### Cost Observations

- Model mix: primarily Sonnet 4.6 (GSD balanced profile)
- Sessions: ~3 sessions (2026-04-02)
- Notable: 2-phase milestone executed in a single day; parallel executor agents for Wave 1 saved meaningful wall-clock time

---

## Milestone: v1.2 — Now Playing Status

**Shipped:** 2026-04-03
**Phases:** 4 (6, 7, 8, 8.1) | **Plans:** 9 | **LOC:** ~1,754 total (+541 from v1.1)

### What Was Built

- `track_change` and `eval_result` SSE events emitted in all daemon poll_loop branches — every track gets both events regardless of outcome
- `now_playing.json` file snapshot written on track detection (evaluating) and overwritten after evaluation — decoupled hydration from SSE stream
- Shared spotipy token cache between daemon and web_ui via Docker volume — single `make auth` flow covers both containers
- `GET /now-playing` hydration endpoint returning current track + eval state from snapshot file; `POST /skip` calling Spotify API directly from web_ui
- Now-playing card with eval-state badge state machine (evaluating → passed / no-lyrics / skipped) wired to both hydration and SSE
- Manual skip button with in-flight disabled state; skip counter bypass preserved
- `severity` field propagated into all 8 eval_result/now_playing call sites in daemon.py
- Multi-badge flex container (`badge-group`) in dashboard; amber "Mild language" badge alongside green "Passed" for severity >= 1 tracks
- Phase 8.1 inserted mid-milestone as a decimal phase (8.1) — first use of the decimal insertion pattern

### What Worked

- **Dual delivery model (SSE + file snapshot)** — SSE for real-time updates, file for hydration; each solves a different problem cleanly without coupling. No complex state sync needed between containers
- **Decimal phase insertion (8.1)** — the allow-reason context feature fit cleanly as 8.1 without disrupting the 8→9 numbering; the pattern works for urgent mid-stream scope
- **TDD still paying off** — severity propagation (Plan 8.1-01) used the existing xfail test scaffold from Phase 6; adding assertions before implementation caught an out-of-scope branch immediately
- **`severity=0` sentinel decision** — using 0 as "no scan ran" instead of making the field optional means frontend never needs to handle missing key; small decision, large downstream simplicity
- **Multi-badge additive pattern** — designing badge-group as additive (criteria badges alongside eval_state badge) instead of replacing means v1.3 drug/sexual badges slot in with no refactor

### What Was Inefficient

- **OAuth scope gap on cold start** — `setup_auth.py` requested `user-read-currently-playing` instead of `user-read-playback-state`; `sp.current_playback()` silently needs the broader scope. Only caught during UAT cold start. Scope requirements should be validated in the TDD scaffold before implementation
- **Phase 7 marked incomplete in ROADMAP** — Phase 7 was complete but its checkbox wasn't updated; the ROADMAP showed `[ ]` Phase 7 when Phase 8 was already done. Plan to auto-check on SUMMARY.md creation
- **Roadmap analyzer failing on `<details>` sections** — `gsd-tools roadmap analyze` returned 0 phases because it couldn't parse phases inside `<details>` HTML tags. Required manual verification for the milestone readiness check

### Patterns Established

- **Dual delivery: SSE events + file snapshot** — SSE for real-time; file snapshot for hydration/reconnect. Any real-time feature that needs page-load state should use this pattern
- **Decimal phase insertion** — urgent mid-stream scope goes in as `N.1` without disrupting milestone numbering; CONTEXT.md `depends on: Phase N` makes the dependency clear
- **Field presence over optional fields** — when a field may not have a meaningful value (e.g., severity when no scan ran), use a sentinel (0, empty string) rather than omitting the field; consumers never need null checks
- **Criteria badge additive model** — evaluation result badge is the primary; content signal badges (mild language, drug reference, etc.) are additive overlays; purge-then-conditionally-append makes the function idempotent

### Key Lessons

1. **OAuth scope must match the Spotipy method, not the endpoint name** — `sp.current_playback()` calls `/v1/me/player` (needs `user-read-playback-state`), not `/v1/me/player/currently-playing` (needs `user-read-currently-playing`); verify scope against Spotipy source, not the Spotify docs endpoint name
2. **Snapshot file + SSE is a better pattern than SSE-only for dashboard state** — pure SSE dashboards go blank on reconnect; a file snapshot that SSE overwrites gives you hydration for free
3. **The Docker shared volume is the simplest token sharing solution** — no token proxy, no API, no copy; mount the same cache path in both containers. Works because spotipy token format is stable
4. **Additive badge design beats replacement design** — if badge state is modeled as "replace current badge," adding a second simultaneous badge requires redesign; additive from day 1 costs nothing extra upfront

### Cost Observations

- Model mix: Sonnet 4.6 (GSD balanced profile)
- Sessions: ~6 sessions (2026-04-03, single day)
- Notable: 9 plans in one day; parallel wave execution and TDD scaffolding kept each plan scoped to 1-2 files max

---

## Milestone: v1.3 — Drug & Sexual Reference Detection

**Shipped:** 2026-04-04
**Phases:** 5 (9–13) | **Plans:** 8 | **Tasks:** 16 | **Quick Tasks:** 1

### What Was Built

- `TrackEvalResult` frozen dataclass replacing positional 3-tuple — named attribute access at all 5 return sites and 10 test mocks
- `DrugScanner` with 19-term conservative keyword set, word-boundary regex; `SexualContentScanner` with 36-term set strictly disjoint from profanity `SEVERITY_MAP`
- Five-tier `ContentChecker` pipeline — explicit → profanity → drug → sexual → allow, with no short-circuit (all three scanners always called)
- `_emit_eval_result` helper propagating four boolean signals through all eval_result SSE events, skip_events.jsonl, and now_playing.json
- Purple "Drug reference" and pink "Sexual content" CSS badge classes + JS detection branches in dashboard skip feed
- Title+artist fallback scan when lyrics unavailable (quick task — catches "Cocaine" et al before returning lyrics_unavailable)

### What Worked

- **TDD RED/GREEN discipline** — RED tests in Plans 11-01 and 12-01 precisely defined the integration contracts before wiring; GREEN plans were surgical 1-2 file changes
- **No-short-circuit scan contract** — running all three scanners unconditionally before the priority decision tree prevented a class of bugs where early-exit would mask simultaneous signals
- **Disjoint keyword set enforced by test** — placing `test_sexual_terms_disjoint_from_severity_map` as the first test in the file made overlap impossible to ship accidentally
- **Decimal phase pattern mature** — Phase 9 (dataclass refactor) inserted cleanly before the scanner phases with no numbering friction; the pattern has become routine
- **Quick task for hotfix scope** — title-fallback scan was a focused change (1 file, 6 tests) that didn't warrant a full phase; `/gsd:quick` handled it in ~4 min with atomic commits and STATE.md tracking

### What Was Inefficient

- **UAT file pre-created but empty** — the `13-HUMAN-UAT.md` file was created with `[awaiting human testing]` status rather than a pending test list; the verify-work workflow had to be resumed rather than started fresh, adding a small friction point
- **`milestone complete` CLI didn't delete originals** — ROADMAP.md and REQUIREMENTS.md were archived but not removed by the CLI; required manual deletion. The CLI contract should complete the full archival cycle
- **STATE.md progress percent always 0** — the progress percent field stays at 0 across the milestone; the state-snapshot tool returns nulls for current position once all phases complete; routing logic works around it but the display is misleading

### Patterns Established

- **Five-tier scan with no short-circuit** — profanity → drug → sexual all run before the priority decision; the `_all_signals` pattern scales to N scanners without changing the decision tree structure
- **`severity=0` sentinel for non-profanity scanners** — any scanner that fires without a profanity score returns `severity=0` in `TrackEvalResult`; consumers never need null checks
- **Title-fallback scan as zero-cost lyric gate** — when LRCLIB returns no lyrics, scan `f"{track} {artist}"` through all active scanners before returning `lyrics_unavailable`; catches high-signal titles at negligible cost
- **Four-boolean schema in all event paths** — explicit, profanity, drug_reference, sexual_content propagated to every event emission and file write; adding a fifth signal in v1.4 requires one field addition, not a schema migration

### Key Lessons

1. **Define the multi-scanner contract before the first scanner ships** — the no-short-circuit rule and boolean schema were established in Phase 9's dataclass; retrofitting them after Phase 10 would have required touching all call sites twice
2. **Keyword disjointness is a test, not a code review** — overlapping terms between scanners produce incorrect severity scores silently; a unit test is the only reliable guard
3. **Quick task scope belongs in GSD, not ad-hoc patches** — the title-fallback was a one-file change but got atomic commits, a SUMMARY.md, and STATE.md tracking; same guarantees as a full phase, at a fraction of the overhead
4. **Badge label wording is a UX decision, not a formatting choice** — "Drug reference" vs "Flagged: Drug reference" affects how parents read the skip feed; make it explicit in the design context, not implicitly in the JS

### Cost Observations

- Model mix: Sonnet 4.6 (GSD balanced profile throughout)
- Sessions: ~4 sessions (2026-04-03 → 2026-04-04, 2 days)
- Notable: 8 plans in 2 days; TDD RED/GREEN split (Plans 01 + 02 per phase) kept each plan to a single behavioral change; quick task added zero session overhead

---

## Milestone: v1.4 — Dashboard Polish & Filter Profiles

**Shipped:** 2026-04-05
**Phases:** 3 (14–16) | **Plans:** 7 | **Tasks:** ~17

### What Was Built

- Idle detection — 3-poll debounce counter + dedup flag in `poll_loop`; daemon writes idle state to `now_playing.json`; dashboard now-playing card transitions to "Nothing playing" within ~5s
- `GET /feed` endpoint returning last 20 skip/five_skip_warning events from `events.jsonl` with monotonic integer IDs; `_init_event_counter()` recovers counter on restart
- `hydrateFeed()` in dashboard — fetches history on page load and SSE reconnect with event-ID dedup via Set, `prependWarningItem()` for five_skip_warning rendering, 20-item DOM cap
- `ContentChecker` profile awareness — `explicit_skip: bool = True` param; `PROFILE_MAP` with 4 named presets; `_build_content_checker()` reconstructs only the wrapper (not scanners) on profile change
- `POST /profile` and `GET /profile` endpoints — frozenset validation, read-merge-write `_save_state_merge({'active_profile': ...})`; `__PROFILE_INITIAL__` injected into HTML by `dashboard()` route
- Split-button FSM/profile compound element — left zone toggles FSM, right zone ▾ opens CSS custom dropdown with active-profile checkmark; attached corner styling via `dropdown-open` class; closes on outside-click, Escape, and SSE disconnect

### What Worked

- **TDD RED/GREEN discipline consistent** — both backend plans (16-01, 16-02) used RED-first TDD; tests precisely defined the API contract before wiring, making GREEN phase surgical
- **PROFILE_MAP + _build_content_checker() separation** — scanner objects (heavy) are long-lived; only the ContentChecker wrapper is rebuilt on profile change. This made the implementation simple and zero-regression by default
- **Split-button human checkpoint** — the checkpoint caught two real issues (button text color not inheriting, dropdown too wide and unattached) that wouldn't have been caught by automated tests. The checkpoint paid for itself immediately
- **`_save_state_merge` pattern** — reusing the existing read-merge-write helper for `active_profile` meant profile persistence required ~3 lines of new code and zero risk of clobbering other state keys
- **Monotonic event IDs + Set-based dedup** — simpler than UUIDs, survives restart via file scan, and the Set dedup on reconnect merge is O(1) per event

### What Was Inefficient

- **Web UI test fixtures were broken before this milestone** — the `client` fixture was patching a non-existent `sp` attribute; 16-02 executor had to fix this as a deviation. A regression test on the fixture shape would have caught this in v1.3
- **`__PROFILE_INITIAL__` placeholder missed in plan's `files_modified`** — plan 16-02 listed `web_ui/main.py` as the only file but the injection code is useless without the placeholder in `index.html`; executor had to add it as an unlisted deviation. Plan checker should flag "injection of X requires X's container file to be listed"
- **Post-checkpoint UI fixes not in plan** — color inheritance (`color: inherit` on `<button>`) and dropdown width/corner attachment were discovered only during human verification. These are predictable CSS pitfalls that could have been in the plan's acceptance criteria

### Patterns Established

- **Debounce counter + dedup flag for SSE state transitions** — `idle_counter` tracks consecutive empty polls; `was_idle` prevents re-emitting idle on already-idle polls; pattern generalizes to any debounced dashboard state change
- **Feed hydration pattern** — `fetch /feed → build Set of existing data-event-id → filter+reverse → render via prepend functions`; reusable for any paginated event feed backed by JSONL
- **Split-button compound element** — `fsm-btn-wrapper` (position:relative) contains `.fsm-split` + `.profile-dropdown`; `dropdown-open` class on `.fsm-split` drives corner-radius transition; `openDropdown()`/`closeDropdown()` helper functions centralize all state mutation (hidden, aria-expanded, class toggle)
- **`color: inherit` on `<button>`** — browsers don't inherit color into `<button>` elements; any compound element that sets color on a container and uses `<button>` children needs `color: inherit` explicitly

### Key Lessons

1. **`<button>` doesn't inherit color — always add `color: inherit`** — this is a browser default that bites compound elements; should be in every plan that introduces a new `<button>` inside a styled container
2. **Injection code requires the injection target to be listed in `files_modified`** — if plan N injects a placeholder into file F, F must be in `files_modified`; otherwise the plan's acceptance criteria can't verify the injection
3. **Human checkpoints are most valuable for visual state interactions** — automated tests couldn't have caught the `dropdown-open` corner attachment issue or the color inheritance bug; the checkpoint discovered both in under 2 minutes
4. **Profile map + wrapper reconstruction is the right pattern for swappable rule engines** — separating the profile selection concern (which rules?) from the scanner concern (how to scan?) keeps both simple; profile change is O(1) ContentChecker rebuild, not O(N) scanner teardown

### Cost Observations

- Model mix: Sonnet 4.6 (GSD balanced profile throughout)
- Sessions: ~2 sessions (2026-04-04 → 2026-04-05, 2 days)
- Notable: 7 plans in 2 days; Wave 1 parallelization (16-01 + 16-02) saved ~10 min of sequential wait; human checkpoint on 16-03 caught 2 real UI bugs that would have required a gap-closure phase otherwise

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~8 | 3 | First milestone; GSD coarse granularity established |
| v1.1 | ~3 | 2 | TDD RED/GREEN discipline adopted; parallel wave execution |
| v1.2 | ~6 | 4 | Dual delivery (SSE + snapshot) pattern; decimal phase insertion; additive badge model |
| v1.3 | ~4 | 5 | No-short-circuit multi-scanner contract; four-boolean schema; quick task scope for hotfixes |
| v1.4 | ~2 | 3 | Profile map + wrapper reconstruction pattern; human checkpoint for visual state interactions |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|--------------------|
| v1.0 | manual UAT | — | 0 (all deps intentional) |
| v1.1 | pytest (healthcheck + Sonos probe) | targeted | pytest, pytest-asyncio |
| v1.2 | pytest (13 daemon event tests, 4 web_ui endpoint tests) | targeted | spotipy (web_ui container) |
| v1.3 | pytest (13 content_checker + 13 drug + 10 sexual + 23 daemon = 59+ tests) | targeted | 0 (no new deps) |
| v1.4 | pytest (82 passing — 16 content_checker, 8 web_ui profile, 13 feed endpoint, 45 others) | targeted | 0 (no new deps) |

### Top Lessons (Verified Across Milestones)

1. Design for the container/process boundary from day 1 — asyncio queues don't cross walls
2. Hardware discovery needs manual override escape hatches from day 1
3. Test runner must be in the container image — verify with `docker compose run` before writing tests
4. OAuth scope must match the Spotipy method signature, not the Spotify docs endpoint name — verify against Spotipy source
5. Snapshot file + SSE is more resilient than SSE-only for dashboard state — hydration on reconnect is free
6. Define the multi-scanner integration contract (no short-circuit, boolean schema) before the first scanner ships — retrofitting is expensive
7. Keyword disjointness between scanner term sets is a unit test, not a code review — silent overlap produces wrong severity scores
8. `<button>` elements don't inherit color from parent — always add `color: inherit` on compound button children
9. Plan `files_modified` must include any file that receives an injected placeholder — otherwise acceptance criteria can't verify the injection
