---
phase: 32-frontend-id-persistence
reviewed: 2026-05-01T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/test_web_ui_endpoints.py
  - web_ui/main.py
  - web_ui/templates/login.html
findings:
  critical: 1
  warning: 5
  info: 2
  total: 8
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-05-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed: the FastAPI application (`web_ui/main.py`), the login page template (`web_ui/templates/login.html`), and the test suite (`tests/test_web_ui_endpoints.py`). The Phase 32 feature additions — the `/login` page, `GET /` redirect-instead-of-401, and `POST /login` cookie flow — are structurally sound. However, two async test functions lack `@pytest.mark.asyncio` and will silently never run, leaving supervisor/subscriber teardown coverage nonexistent. One supervisor restart loop has a logic defect that causes infinite rapid-fire restarts after a spawn failure. One route is missing a `FileNotFoundError` guard. The remaining findings are quality concerns.

---

## Critical Issues

### CR-01: Two async tests silently never execute — supervisor teardown and uid isolation have zero real coverage

**File:** `tests/test_web_ui_endpoints.py:369` and `tests/test_web_ui_endpoints.py:397`

**Issue:** `test_last_subscriber_removal_cancels_tail_task` (line 369) and `test_two_uids_get_independent_tail_tasks` (line 397) are declared as `async def` but have no `@pytest.mark.asyncio` decorator (and no `asyncio_mode = "auto"` pytest configuration was found). Without the decorator, pytest-asyncio does not run these functions as coroutines — it collects them as regular sync tests that return coroutine objects. A coroutine object is truthy, so the tests appear to pass immediately without executing a single assertion. The teardown behavior verified by `test_last_subscriber_removal_cancels_tail_task` (D-07: "cancel tail task when last subscriber disconnects") and the uid isolation verified by `test_two_uids_get_independent_tail_tasks` are entirely untested against the actual implementation.

**Fix:** Add `@pytest.mark.asyncio` to both functions:

```python
import pytest

@pytest.mark.asyncio
async def test_last_subscriber_removal_cancels_tail_task(mock_ctx):
    ...

@pytest.mark.asyncio
async def test_two_uids_get_independent_tail_tasks():
    ...
```

If the project uses pytest-anyio or asyncio mode auto, add `asyncio_mode = "auto"` to `pytest.ini` / `pyproject.toml` instead. Verify with `pytest -v tests/test_web_ui_endpoints.py -k "cancels_tail"` — with the bug present, the test "passes" instantly; after the fix it should take a measurable fraction of a second.

---

## Warnings

### WR-01: Supervisor enters tight restart loop after spawn failure — stale dead process re-awaited

**File:** `web_ui/main.py:266-278`

**Issue:** When `_spawn_daemon(uid)` raises in the `_supervisor_for_uid` restart path (lines 269-277), the code logs the error, sleeps 30 seconds, and `continue`s the outer `while True`. On the next iteration, `proc = _daemons.get(uid)` (line 243) returns the **old, already-exited process** because the failed spawn never replaced it in `_daemons`. `await proc.wait()` on a finished process returns immediately with the same exit code. If that exit code is still unexpected (non-0, non-2), the supervisor tries to spawn again — fails again — sleeps 30 seconds — and so on indefinitely. The 30-second back-off does limit the damage, but the root issue is that `_daemons[uid]` is never cleaned up after a failed spawn, so the dead process is re-evaluated on every loop iteration.

**Fix:** After a failed spawn, remove the stale entry from `_daemons` (or set it to the new attempt's result before awaiting). At minimum, pop the stale entry so the next loop iteration detects `proc is None` and exits the supervisor:

```python
except Exception as spawn_exc:
    log.error(
        "web_ui: supervisor uid=%s — restart spawn failed: %s; retrying in 30s",
        uid, spawn_exc,
    )
    _daemons.pop(uid, None)   # <-- remove stale dead process
    await asyncio.sleep(30)
    continue
```

Alternatively, break out of the loop entirely on repeated spawn failures to avoid an infinite retry cycle with no circuit breaker.

### WR-02: GET /login has no FileNotFoundError guard — missing template causes unhandled 500

**File:** `web_ui/main.py:429-432`

**Issue:** The `login_page()` route opens `login.html` with `open(template_path)` (line 431) inside no try/except. If the template file is missing (e.g., incomplete deployment, wrong working directory), Python raises `FileNotFoundError` uncaught from the route handler. FastAPI will return a 500 Internal Server Error with a generic traceback. By contrast, the `dashboard()` route at line 409-413 already handles this case with a fallback HTML string. The `/login` route is the entry point for all unauthenticated users — a crash here makes the entire UI inaccessible with no diagnostic information to the user.

**Fix:** Mirror the dashboard's pattern:

```python
@app.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    template_path = os.path.join(TEMPLATES_DIR, "login.html")
    try:
        with open(template_path) as f:
            html = f.read()
    except FileNotFoundError:
        html = "<html><body><p>Login page template not installed.</p></body></html>"
    return HTMLResponse(content=html)
```

### WR-03: POST /login sets secure=True cookie — login silently fails over HTTP

**File:** `web_ui/main.py:455`

**Issue:** `POST /login` sets `secure=True` on the uid cookie (line 455). When `secure=True` is set, the browser will silently refuse to store the cookie if the page was served over plain HTTP. The server returns HTTP 200 with `{"ok": True}` and a `Set-Cookie` header, but the browser discards the cookie. The login form JavaScript then calls `window.location.replace('/')`, the dashboard route finds no cookie, and redirects back to `/login` — creating an invisible loop with no error displayed to the user. The same issue affects local development.

Phase 31 deployed HTTPS, so production is protected, but:
1. Any HTTP-only staging or dev environment silently breaks authentication.
2. The test `test_post_login_valid_uid` (line 132) uses `TestClient` which does not enforce the secure attribute, so the test passes even when the cookie would be rejected in a real browser.

**Fix:** Either conditionally set `secure` from an environment variable, or document explicitly that the application requires HTTPS and add a startup check:

```python
secure_cookie = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
response.set_cookie(
    key="uid",
    value=body.uid,
    httponly=True,
    samesite="lax",
    path="/",
    max_age=60 * 60 * 24 * 30,
    secure=secure_cookie,
)
```

### WR-04: KeyError on missing Spotify env vars in /auth/callback leaks env var names to users

**File:** `web_ui/main.py:645-647`

**Issue:** Lines 645-647 use direct dict access (`os.environ["SPOTIFY_CLIENT_ID"]`, etc.) inside the try/except block. If any of these env vars are absent, Python raises `KeyError: 'SPOTIFY_CLIENT_ID'`. This exception is caught by the broad `except Exception as exc` on line 655 and rendered in the user-visible HTML error page as: `"Token exchange failed: 'SPOTIFY_CLIENT_ID'"`. This leaks internal configuration key names to whoever visits the callback URL. It also conflates a configuration error with a Spotify API error, making it harder to diagnose.

**Fix:** Validate env vars before entering the try block and return a distinct error:

```python
client_id = os.environ.get("SPOTIFY_CLIENT_ID")
client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI")
if not all([client_id, client_secret, redirect_uri]):
    log.error("web_ui: Spotify env vars not configured — cannot complete OAuth callback")
    return _error_html(500, "Server configuration error — please contact the operator")
try:
    paths = _registry.user_paths(uid)
    cache_handler = CacheFileHandler(cache_path=paths["cache_path"])
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        ...
    )
```

### WR-05: test_spawn_daemon_writes_pid_file asserts only existence of _spawn_daemon — PID file write never verified

**File:** `tests/test_web_ui_endpoints.py:631-698`

**Issue:** The test is named `test_spawn_daemon_writes_pid_file` and its docstring says "writes users/{uid}/daemon.pid containing the process PID (D-11)". However, after approximately 60 lines of progressively-abandoned mock setup (which explicitly comments "This is getting complex" and ends with `pass` on line 664), the only actual assertion on line 698 is:

```python
assert hasattr(web_ui_main, "_spawn_daemon"), "_spawn_daemon must exist on web_ui_main module"
```

This means requirement D-11 (PID file written to `users/{uid}/daemon.pid`) has **no functional test coverage at all**. The test passes trivially. Any future refactor that removes the PID write would go undetected.

**Fix:** Replace the abandoned mock chain with a clean test using `tmp_path` and patching only what's necessary:

```python
async def test_spawn_daemon_writes_pid_file(tmp_path):
    uid = "pidtestuid"
    user_dir = tmp_path / "users" / uid
    user_dir.mkdir(parents=True)
    fake_paths = {
        "state_path": str(tmp_path / "state.json"),
        "events_path": str(tmp_path / "events.jsonl"),
        "cache_path": str(tmp_path / ".cache"),
    }
    mock_proc = MagicMock()
    mock_proc.pid = 42000
    from unittest.mock import AsyncMock, patch
    with patch.object(web_ui_main._registry, "user_paths", return_value=fake_paths), \
         patch("main.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)), \
         patch("main.pathlib.Path") as mock_path_cls:
        # Point __file__ resolution to tmp_path so PID file lands in user_dir
        ...
        await web_ui_main._spawn_daemon(uid)
    pid_file = user_dir / "daemon.pid"
    assert pid_file.exists(), "daemon.pid must be written"
    assert pid_file.read_text() == "42000"
```

The exact mock strategy will depend on how `pathlib.Path(__file__).parent.parent` is resolved; the core requirement is that the PID file assertion is present and validated.

---

## Info

### IN-01: Dead code in test_spawn_daemon_sets_env_vars — unreachable branch left in place

**File:** `tests/test_web_ui_endpoints.py:615`

**Issue:** Line 615 contains `_asyncio.coroutine(lambda *a, **kw: mock_proc) if False else None`. The `if False` branch is provably unreachable and is immediately overwritten by the `AsyncMock` assignment on line 618. This appears to be a leftover from an earlier draft. It adds noise and could confuse future readers into thinking `_asyncio.coroutine` is intentionally referenced.

**Fix:** Remove line 615 entirely. The test already correctly uses `AsyncMock` on line 618.

### IN-02: Callback test fake_paths dicts omit now_playing_path — inconsistent with real user_paths contract

**File:** `tests/test_web_ui_endpoints.py:443-447`, `467-471`, `530-534`, `550-554`, `570-574`, `606-610`, `635-639`, `908-912`

**Issue:** All `fake_paths` dicts in callback and spawn-related tests omit `"now_playing_path"`, but the real `UserRegistry.user_paths()` always returns this key (confirmed in `user_registry.py:101`). The omission doesn't currently cause test failures because the callback route and `_spawn_daemon` only access `cache_path`, `state_path`, and `events_path`. However, if any future refactor makes the callback or spawn path build a `UserContext` object (as `dashboard()` does at line 400-406), the missing key will trigger the `except KeyError` path in `get_user_context` and return a 500 instead of the expected 302 — a silent regression that tests would miss.

**Fix:** Add `"now_playing_path"` to all callback `fake_paths` dicts to match the real contract:

```python
fake_paths = {
    "state_path": str(tmp_path / "state.json"),
    "events_path": str(tmp_path / "events.jsonl"),
    "now_playing_path": str(tmp_path / "now_playing.json"),   # <-- add this
    "cache_path": str(tmp_path / "token_cache" / ".cache"),
}
```

---

_Reviewed: 2026-05-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
