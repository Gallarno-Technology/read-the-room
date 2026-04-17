---
phase: 27-user-registry-operator-cli
verified: 2026-04-16T22:30:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 27: User Registry + Operator CLI Verification Report

**Phase Goal:** An operator can provision a new user, inspect the registry, and remove a user — all data properly namespaced and isolated on disk
**Verified:** 2026-04-16T22:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | A uid can be generated and results in a users/{uid}/ directory tree on disk | VERIFIED | `UserRegistry.provision()` calls `_scaffold_user_dir()` which runs `os.makedirs` for `data/` and `token_cache/`; test_provision_creates_directory passes |
| 2  | users.json at project root contains the uid entry after provisioning | VERIFIED | `_save()` writes `{"users": [...]}` to `users.json`; test_provision_writes_users_json passes |
| 3  | users.json is never partially written — atomic temp-file swap on every write | VERIFIED | `_save()` writes to `.json.tmp` then calls `os.replace()`; test_provision_atomicity confirms `.tmp` absent after write |
| 4  | lyrics_cache.db path is NOT created inside any per-user directory | VERIFIED | `_scaffold_user_dir()` creates only `state.json`, `data/events.jsonl`, `data/now_playing.json`, `token_cache/`; test_lyrics_cache_not_in_user_dir passes |
| 5  | Removing a uid deletes users/{uid}/ and removes the entry from users.json | VERIFIED | `remove()` calls `shutil.rmtree()` then `_save(remaining)`; test_remove_deletes_directory and test_remove_updates_registry pass |
| 6  | `python scripts/manage_users.py generate-url alice` prints a uid and a valid Spotify OAuth URL containing that uid in the `state` parameter | VERIFIED | `cmd_generate_url()` calls `SpotifyOAuth(..., state=uid)` and prints uid + URL; test_generate_url_output_contains_uid and test_generate_url_output_contains_state_param pass |
| 7  | After generate-url, users/{uid}/ directory tree exists with all required files | VERIFIED | `cmd_generate_url()` calls `registry.provision(name)` which scaffolds the full tree; test_generate_url_creates_user_dir passes |
| 8  | After generate-url, users.json at project root contains the uid entry with status=pending | VERIFIED | `provision()` sets `status="pending"`; test_generate_url_status_pending passes |
| 9  | `python scripts/manage_users.py remove <uid>` deletes the user directory and removes the registry entry | VERIFIED | `cmd_remove()` calls `registry.remove(uid)`; test_remove_deletes_directory and test_remove_valid_uid_returns_0 pass |
| 10 | generate-url with 5 existing users prints an error and exits non-zero — no 6th user created | VERIFIED | `provision()` raises `RuntimeError("User limit reached (max 5)")` when `len(users) >= MAX_USERS`; `cmd_generate_url()` catches it and returns 1; test_generate_url_limit_returns_1 passes |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `user_registry.py` | UserRegistry class with provision(), remove(), load(), user_paths() | VERIFIED | 119 lines; all four methods present; MAX_USERS=5 constant; atomic write via os.replace() |
| `tests/test_user_registry.py` | 17 tests covering all registry behaviors | VERIFIED | 176 lines; 17 tests collected and passing |
| `scripts/manage_users.py` | Operator CLI with generate-url and remove subcommands | VERIFIED | 142 lines; both subcommands implemented; usage() guard present |
| `scripts/__init__.py` | Empty package marker | VERIFIED | Exists at 0 bytes — correct empty package marker |
| `tests/test_manage_users.py` | 10 integration tests for CLI subcommands | VERIFIED | 152 lines; 10 tests collected and passing |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `user_registry.py` | `users.json` | `os.replace()` atomic write | VERIFIED | `_save()` at line 112-118: writes `.json.tmp` then calls `os.replace(tmp_path, self._registry_path)` |
| `user_registry.py` | `users/{uid}/` | `os.makedirs` for data/, token_cache/ | VERIFIED | `_scaffold_user_dir()` at lines 93-110: `os.makedirs(data_dir)` and `os.makedirs(token_dir)` |
| `scripts/manage_users.py` | `user_registry.UserRegistry` | import from project root | VERIFIED | Line 25: `from user_registry import MAX_USERS, UserRegistry`; sys.path.insert ensures project root is on path |
| `scripts/manage_users.py` | `SpotifyOAuth.get_authorize_url()` | `state=uid` kwarg | VERIFIED | Lines 63-72: `SpotifyOAuth(..., state=uid)` then `auth_manager.get_authorize_url()` |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no UI components or data-rendering artifacts. All outputs are disk writes (files) and stdout prints, verified directly by tests.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `user_registry` module imports cleanly | `.venv/bin/python -c "from user_registry import UserRegistry, MAX_USERS; assert MAX_USERS == 5"` | `import ok, MAX_USERS=5` | PASS |
| CLI prints usage and exits 1 on no-args | `.venv/bin/python scripts/manage_users.py` | Printed usage, exit 1 | PASS |
| No test data leaked to project root | `ls users.json users/ 2>/dev/null` | Neither path exists | PASS |
| Full test suite 27/27 pass | `.venv/bin/python -m pytest tests/test_user_registry.py tests/test_manage_users.py -v` | `27 passed in 0.10s` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ISOL-01 | 27-01 | Provisioned user has an isolated data directory (`users/{uid}/`) containing their own `state.json`, `data/events.jsonl`, `data/now_playing.json`, and `token_cache/` | SATISFIED | `_scaffold_user_dir()` creates the full tree; test_provision_creates_directory, test_provision_creates_state_json, test_provision_creates_data_files, test_provision_creates_token_cache_dir all pass |
| ISOL-02 | 27-01 | A flat registry (`users.json`) maps each uid to name and created_at timestamp | SATISFIED | `provision()` appends `{uid, name, created_at, status}` to users.json via `_save()`; test_provision_writes_users_json passes |
| ISOL-03 | 27-01 | `lyrics_cache.db` is shared across all users, keyed by Spotify track ID — NOT per-user | SATISFIED | No code in `user_registry.py` or `scripts/manage_users.py` creates or references `lyrics_cache.db`; test_lyrics_cache_not_in_user_dir explicitly asserts absence and passes |
| OPS-01 | 27-02 | Operator can run `manage_users.py generate-url <name>` to print a new uid and Spotify OAuth URL with that uid baked into the `state` parameter | SATISFIED | `cmd_generate_url()` provisions user, builds SpotifyOAuth with `state=uid`, prints uid and URL; 6 tests covering this path all pass |
| OPS-02 | 27-02 | Operator can run `manage_users.py remove <uid>` to delete their data directory and remove their registry entry | SATISFIED | `cmd_remove()` delegates to `registry.remove(uid)` which runs `shutil.rmtree` + atomic save; test_remove_valid_uid_returns_0 and test_remove_deletes_directory pass |

No orphaned requirements — all 5 IDs (ISOL-01, ISOL-02, ISOL-03, OPS-01, OPS-02) are claimed by a plan and verified in the codebase.

---

### Anti-Patterns Found

None. Scanned `user_registry.py` and `scripts/manage_users.py` for TODO/FIXME/PLACEHOLDER/stub patterns — no matches found.

---

### Human Verification Required

None. All behaviors are fully verifiable programmatically:

- Disk layout verified by test assertions on tmp_path
- Atomic write verified by checking `.tmp` file absence
- OAuth URL `state=` param verified by mock + capsys
- User limit enforced by RuntimeError caught in tests

---

### Gaps Summary

No gaps. All 10 must-haves from both plans are verified against the actual codebase. The 5 requirement IDs are all satisfied. The test suite (27 tests) passes in 0.10s with no failures.

---

_Verified: 2026-04-16T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
