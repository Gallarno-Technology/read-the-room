# Phase 29: OAuth Onboarding Flow - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `GET /auth/callback` to `web_ui/main.py`. This endpoint receives Spotify's OAuth
redirect, validates the `state` parameter matches a pending uid in `users.json`, exchanges
the authorization code for a token via spotipy, writes the token to
`users/{uid}/token_cache/.cache`, flips the uid's status to `"active"` in `users.json`,
sets the uid httpOnly cookie, spawns the user's daemon process, and redirects to `/`.

No new UI pages, no self-service sign-up, no dashboard changes. The operator still runs
`manage_users.py generate-url <name>` to get the URL; this phase completes the server-side
half of that flow.

</domain>

<decisions>
## Implementation Decisions

### Callback — success response
- **D-01:** On success, return `HTTP 302` redirect to `/` with the uid cookie set.
  Browser lands on the dashboard immediately. Clean, matches AUTH-04.
- **D-02:** Cookie attributes: `uid=<uid>; HttpOnly; SameSite=Lax; Path=/`.
  `Secure` flag deferred to Phase 31 (HTTPS via Caddy is not yet wired).

### Callback — error response
- **D-03:** On any failure (invalid/unrecognized `state`, expired code, Spotify API error,
  token write failure), return a plain HTML error page (400 or 500).
  Keep it human-readable: show the error reason and a "contact the operator" note.
  No JSON errors — user just came from a browser and expects a human-readable page.

### State validation
- **D-04:** Validate `state` by looking up the uid in `users.json` and asserting
  `status == "pending"`. A uid that is already `"active"` or absent → 400 error.
  No in-memory pending-auth map required for a 5-user manual onboarding workflow;
  the atomicity guarantee comes from the `_save()` atomic-write pattern in `UserRegistry`.
- **D-05:** AUTH-02 is satisfied by the uid travelling via OAuth `state` param (already
  wired in Phase 27 via `SpotifyOAuth(state=uid)`). The callback reads
  `request.query_params["state"]` to recover the uid without any extra encoding.

### Token exchange
- **D-06:** Use spotipy `SpotifyOAuth` with `CacheFileHandler(cache_path=users/{uid}/token_cache/.cache)`.
  Call `get_access_token(code)` — this writes the token to the cache file automatically.
  Do NOT instantiate a long-lived auth manager at module level; build it per-request in the
  callback handler to avoid holding stale tokens in memory.
- **D-07:** After token exchange, call `registry.activate(uid)` (or inline: load → update
  status → atomic save) to flip `status` from `"pending"` to `"active"`.
  Only after status is `"active"` does `get_user_context` allow the uid through (Phase 28 D-02).

### Daemon spawn
- **D-08:** Phase 29 spawns the daemon with `asyncio.create_subprocess_exec` (stdlib —
  consistent with the v1.8 Roadmap decision). The spawn is fire-and-forget in Phase 29;
  Phase 30 adds supervision (restart-on-crash, boot-time re-launch). Phase 29 just needs
  the process running.
- **D-09:** Daemon env vars passed at spawn: `STATE_PATH`, `EVENTS_PATH`, `EVENTS_PATH`,
  `LYRICS_DB_PATH`, `SPOTIFY_CACHE_PATH` — resolved from `UserRegistry.user_paths(uid)`.
  All other env vars (Spotify credentials, `POLL_INTERVAL_SECONDS`) are inherited from the
  parent process environment.
- **D-10:** Daemon spawn is async — callback redirects to `/` immediately after cookie set;
  it does not wait for the daemon to finish starting. If spawn fails (OSError, missing
  daemon script), log the error but still redirect to `/`. The user can still see the
  dashboard; the daemon will be re-spawned when Phase 30 adds boot-time supervision.

### Claude's Discretion
- Exact spotipy `SpotifyOAuth` constructor args in the callback (client_id, secret, redirect_uri
  are read from the same env vars as `_sp_init()`; scope must match what `manage_users.py` used)
- HTML error page styling (plain `<pre>` or minimal styled HTML — consistent with the
  existing minimal frontend aesthetic)
- Whether `registry.activate(uid)` is a new `UserRegistry` method or inline in the callback
- Exact FastAPI response type for the redirect (`RedirectResponse` from starlette)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — AUTH-01, AUTH-02, AUTH-03 (Phase 29 requirements)

### Existing OAuth pattern (reference, not reuse)
- `setup_auth.py` — Single-user OAuth pattern using `SpotifyOAuth` + `CacheFileHandler`;
  callback handler in Phase 29 uses the same pattern server-side (code exchange, not interactive)

### Phase 27 outputs (registry + URL generation)
- `user_registry.py` — `UserRegistry.provision()`, `UserRegistry.load()`, `UserRegistry.user_paths(uid)`,
  `UserRegistry._save()` atomic write; Phase 29 needs to add `activate(uid)` or inline equivalent
- `scripts/manage_users.py` — Shows `SpotifyOAuth(state=uid)` pattern for URL generation;
  callback receives `state=uid` back from Spotify

### Phase 28 outputs (routing and cookie consumption)
- `web_ui/main.py` — `get_user_context()` Depends reads the uid cookie and checks `status == "active"`;
  callback must set the cookie before redirecting so the first `GET /` request is authenticated
- `.planning/phases/28-cookie-routing-per-user-sse/28-CONTEXT.md` — D-01 (401 for pending/unknown uid),
  D-02 (pending uid treated same as unknown), and the deferred note "Cookie write (setting uid httpOnly
  cookie after OAuth) — Phase 29"

### Pitfalls (from STATE.md)
- `spotipy CacheFileHandler` has no file locking — daemon must own token refresh; web_ui spotipy
  should not trigger refreshes. In the callback, `get_access_token(code)` is a one-time write;
  after that, only the daemon's auth manager should refresh.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `user_registry.py` — `UserRegistry.load()` + atomic `_save()` pattern; `user_paths(uid)` returns
  all per-user paths needed for daemon env vars; Phase 29 needs an `activate(uid)` helper or can do
  the load/update/save inline in the callback
- `web_ui/main.py` `_sp_init(cache_path)` — same env var loading pattern reusable for callback's
  token exchange (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)
- FastAPI `RedirectResponse` from starlette — standard pattern for HTTP redirects in FastAPI

### Established Patterns
- All file writes in `UserRegistry` go through the atomic temp-file + `os.replace()` pattern — Phase 29
  must use the same approach when updating `users.json`
- `asyncio.create_subprocess_exec` is the chosen daemon spawn mechanism (v1.8 Roadmap decision;
  Phase 30 extends with supervision)
- `load_dotenv()` at module top — env vars already loaded when callback runs; no extra loading needed

### Integration Points
- `GET /auth/callback` → new route in `web_ui/main.py`
- `user_registry.py` → `activate(uid)` or inline update of user record
- `asyncio.create_subprocess_exec(sys.executable, "daemon.py", ...)` → daemon spawn
- `Response.set_cookie(key="uid", value=uid, httponly=True, samesite="lax", path="/")` → cookie write
- Phase 30 will replace/extend the bare `create_subprocess_exec` call with a supervisor coroutine;
  Phase 29 just needs the process running

</code_context>

<specifics>
## Specific Ideas

- The callback URL path is `/auth/callback` — must match `SPOTIFY_REDIRECT_URI` in `.env`
- `state` param arrives as a query parameter: `request.query_params.get("state")` (FastAPI/Starlette)
- `code` arrives as: `request.query_params.get("code")`
- Spotify also sends `error` instead of `code` when the user declines consent — handle this case too
  (return error HTML with "Authorization was denied" message)
- The daemon script lives at `daemon.py` in the project root (or `web_ui/../daemon.py` relative to
  `web_ui/`); use `pathlib.Path(__file__).parent.parent / "daemon.py"` to build the path

</specifics>

<deferred>
## Deferred Ideas

- In-memory pending-auth map (CSRF protection) — not needed for 5-user trusted manual workflow
- `Secure` cookie flag — deferred to Phase 31 (HTTPS)
- Error page styling beyond minimal HTML — Phase 32 frontend polish
- Retry / re-authorize link on error page — operator handles this manually

None outside the above — discussion stayed within phase scope.
</deferred>

---

*Phase: 29-oauth-onboarding-flow*
*Context gathered: 2026-04-18*
