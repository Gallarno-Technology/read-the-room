# Pitfalls Research

**Domain:** Open sourcing a private Python/Docker home automation tool (Read the Room / spotify-sentiment)
**Researched:** 2026-04-06
**Confidence:** HIGH — findings based on direct inspection of this repository's actual state, not generic advice

---

## Critical Pitfalls

### Pitfall 1: .env File Copied Into Docker Image (No .dockerignore)

**What goes wrong:**
The Dockerfile uses `COPY . .` with no `.dockerignore` present. Every file in the project root — including `.env` (which contains real Spotify OAuth credentials) — gets baked into the Docker image layers. Anyone who pulls the image or inspects its layers can extract the credentials. This is true even if `.env` is in `.gitignore`: Docker does not consult `.gitignore`.

This is confirmed in the current codebase: `.dockerignore` does not exist, `.env` exists in the project root with real (non-placeholder) credentials, and `Dockerfile` uses `COPY . .`.

**Why it happens:**
Developers add `.env` to `.gitignore` and assume it's excluded everywhere. Docker has a separate exclusion mechanism (`.dockerignore`) that mirrors `.gitignore` in purpose but is entirely independent.

**How to avoid:**
1. Create a `.dockerignore` file in the project root before any public release. Minimum entries:
   ```
   .env
   token_cache/
   state.json
   lyrics_cache.db
   data/
   .git/
   .venv/
   .planning/
   .claude/
   __pycache__/
   .pytest_cache/
   ```
2. After adding `.dockerignore`, rebuild the image and verify with `docker run --rm <image> cat /app/.env` — should return "No such file."
3. Add a README note that users should never build images from a host directory containing real `.env` credentials if they plan to push images to a public registry.

**Warning signs:**
- `ls .dockerignore` returns "No such file" (confirmed absent right now).
- `docker run --rm <image> cat /app/.env` succeeds and prints credential values.
- CI workflow builds Docker image without gating on `.dockerignore` presence.

**Phase to address:**
Repository hygiene audit — the first phase of v1.6. This must ship before the repo is made public.

---

### Pitfall 2: OAuth Token File Exposed via Docker Build Context

**What goes wrong:**
`token_cache/.cache` contains a live Spotify refresh token (confirmed: 551 bytes, written by a root-owned container). This token grants `user-modify-playback-state` — it can control Spotify playback for the real account. Without `.dockerignore`, `COPY . .` in the Dockerfile copies `token_cache/` into the image if the file exists at build time.

Two specific exposure paths:
- `docker build .` run from the project root while `token_cache/.cache` exists on the host.
- `docker compose build` triggered automatically (e.g., by `make restart`) after initial `make auth`.

**Why it happens:**
`token_cache/` is correctly gitignored, so developers trust it is "excluded." The Docker build context is not the same as the git-tracked set of files — Docker copies everything not excluded by `.dockerignore`, regardless of `.gitignore`.

**How to avoid:**
1. `.dockerignore` must include `token_cache/` (same solution as Pitfall 1).
2. Add a CI check: `test -f .dockerignore && grep -q "token_cache" .dockerignore || (echo "ERROR: token_cache not in .dockerignore" && exit 1)`.
3. Consider adding GitHub's secret scanning / push protection to the repo — it detects Spotipy-format cache files with known token patterns.

**Warning signs:**
- `docker run --rm <image> ls /app/token_cache/` succeeds and lists `.cache`.
- `docker image history <image>` shows a layer with files added from `token_cache/`.

**Phase to address:**
Repository hygiene audit phase (same phase as Pitfall 1).

---

### Pitfall 3: .planning/ and .claude/ Directories Committed to Public Repo

**What goes wrong:**
313 files in `.planning/` and 217 files in `.claude/` are currently tracked by git. These directories contain:
- Absolute paths with the author's username: `/home/cgallarno/Development/spotify-sentiment/...` appears in hundreds of automated verification steps in `.planning/phases/` files.
- GSD workflow tooling (`.claude/`) — project-specific Claude Code scaffolding with internal prompts and tooling that is not part of the project's public interface.
- Milestone planning artifacts, retrospectives, internal notes — confusing to public contributors.

When the repo goes public, these 530 files will appear on GitHub. Contributors will see internal planning docs as the dominant content in the repo. The absolute paths expose the author's home directory username and machine layout.

**Why it happens:**
The `.planning/` and `.claude/` directories were designed for private development workflow management. Public release was not considered when they were first committed.

**How to avoid:**
**Recommended: Add both directories to `.gitignore` and remove from tracking.**
```bash
echo ".planning/" >> .gitignore
echo ".claude/" >> .gitignore
git rm -r --cached .planning/ .claude/
git commit -m "chore: remove internal workflow dirs from public tracking"
```
The directories remain on disk (untracked) for local use. They do not appear on GitHub.

Alternative: Keep `.planning/` public as a project transparency artifact, but this requires replacing all absolute paths (hundreds of occurrences) with relative paths. Not recommended for the time available.

**Warning signs:**
- `git ls-files .planning/` returns any results.
- `git ls-files .claude/` returns any results.
- `grep -rn "cgallarno" .planning/ --include="*.md"` returns matches.

**Phase to address:**
Repository hygiene audit — this should be the first change committed in v1.6, before any other v1.6 content is added.

---

### Pitfall 4: Personal Home IP Address in Test Files

**What goes wrong:**
`192.168.1.164` — the author's actual Living Room Sonos speaker IP — appears in:
- `tests/test_sonos_probe.py`: hardcoded as mock fixture values and in assertion error messages
- `tests/test_sonos_probe.py`: used in `SONOS_SPEAKER_IPS` env var override in test patches

These are private RFC 1918 addresses and pose no direct security risk. However:
- Assertion error messages say "Expected `_ip_cache['Living Room'] == '192.168.1.164'`" — looks like a test written for one specific machine.
- Contributors reading test failures see a specific home IP and may not understand it is a mock value.
- It implicitly suggests the tests are environment-dependent when they are actually fully mocked.

**Why it happens:**
Tests were written against the author's real Sonos setup. The IP was copied directly from the real device. It was never anonymized because the repo was private.

**How to avoid:**
Replace all instances of `192.168.1.164` in test files with `192.168.1.100` (a generic placeholder that is unambiguously an example, not a real device). Run `grep -rn "192\.168\.1\.164" tests/ skip_client.py` after the change to confirm clean.

In `skip_client.py`, the comment already uses `.50`/`.51` which reads as an example — no change needed there.

**Warning signs:**
- `grep -rn "192\.168\.1\.164" tests/ skip_client.py` returns matches.
- Test failure output contains "192.168.1.164" in assertion messages.

**Phase to address:**
Source code sanitization phase of v1.6.

---

### Pitfall 5: GitHub Actions CI Fails Without Real Spotify Credentials

**What goes wrong:**
When adding GitHub Actions CI (a v1.6 goal), common failure modes for this project:

1. **Missing env vars cause import-time failures**: If any module imports spotipy at the top level and initializes with env vars, CI fails with `KeyError` or `SpotifyOauthError` before any test runs.
2. **`docker compose up` in CI with `network_mode: host`**: GitHub Actions macOS/Windows runners do not support `network_mode: host`. If CI runs the full compose stack instead of `pytest` directly, it will fail on non-Linux runners.
3. **Unmocked SSDP discovery**: If `soco.discovery.discover()` is not mocked at the module import level in a test, it will fire real multicast in CI. GitHub Actions runners have no Sonos speakers. The call will return empty or hang.
4. **File path assumptions**: Tests use `tmp_path` fixtures (pytest) for state files — this is correct. Any test that assumes `/app/state.json` exists will fail outside Docker.

**Why it happens:**
The full test suite was designed to run inside the Docker container environment via `make auth` + `docker compose run`. Running `pytest` directly on a CI runner without Docker is a different execution context.

**How to avoid:**
1. Run CI as: `pip install -r requirements.txt && pytest` with dummy env vars in the workflow YAML — not `docker compose run`.
2. Set all required env vars in the workflow `env:` block with clearly fake values:
   ```yaml
   env:
     SPOTIFY_CLIENT_ID: test-client-id
     SPOTIFY_CLIENT_SECRET: test-client-secret
     SPOTIFY_REDIRECT_URI: https://127.0.0.1:8080
     SPOTIFY_CACHE_PATH: /tmp/test-cache
     STATE_PATH: /tmp/test-state.json
     LYRICS_DB_PATH: /tmp/test-lyrics.db
   ```
3. Verify all Sonos SSDP calls are mocked in test fixtures before adding CI.
4. Use `ubuntu-latest` runner to avoid `network_mode: host` issues.

**Warning signs:**
- CI workflow calls `docker compose up` or `docker compose run` in a test step.
- First CI run fails with `SpotifyOauthError` or missing env var traceback.
- `tests/test_sonos_probe.py` takes over 30 seconds in CI (SSDP timeout).

**Phase to address:**
GitHub Actions CI setup phase of v1.6.

---

### Pitfall 6: README Written for Author, Not Strangers

**What goes wrong:**
The current README is functional for someone who already knows the project. A stranger cloning it will encounter:
- No explanation of *why* the project exists or what problem it solves before jumping to Quick Start.
- No mention that Sonos is optional (the service also works with non-Sonos Spotify Connect devices).
- No section explaining what happens if Spotify is not playing (idle state behavior).
- The "browser fails to load the redirect page — this is expected" note is buried in step 5; beginners will panic and abandon the setup before reaching it.
- No troubleshooting for the most common first-run failure: UID/GID not exported before `docker compose up`.

**Why it happens:**
README was written incrementally alongside development for the author's own reference. It documents the correct steps without anticipating where a stranger would get lost.

**How to avoid:**
Rewrite with an explicit "target reader" persona: someone who has Docker, has a Spotify account, and has (or wants to have) a Sonos speaker — but has never seen this project before. Address their first three questions in the opening paragraph: What is this? Does it work on my setup? What do I need?

**Warning signs:**
- README has no "What is this?" section above Quick Start.
- Quick Start step 1 assumes the reader knows what `docker compose` is and has it installed.
- No troubleshooting section for UID/GID, OAuth redirect, or "Sonos not found."

**Phase to address:**
README rewrite phase of v1.6.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| No `.dockerignore` | Simpler initial Dockerfile | `.env` and live OAuth tokens in image on `COPY . .` | Never for public release |
| Absolute paths in `.planning/` automation | Works on author's machine | Breaks for all contributors; exposes username in public repo | Never for public repo |
| Real home IP in test fixtures | Legible test output during dev | Misleads contributors; looks environment-dependent | Never in public tests |
| `.planning/` tracked in git | Internal workflow continuity | 313 planning files dominate GitHub repo view; confuses contributors | Only in private repos |
| Token cache owned by root (container) | Docker bind mount works naturally | Confusing `sudo` requirement for manual inspection | Acceptable with documentation |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Spotify OAuth (spotipy) | Assuming token transfers with the cloned repo | Each user must run `make auth` on their own machine with their own credentials |
| Spotify OAuth (spotipy) | Old `make auth` run before OAuth scope fix | Users who ran `make auth` before v1.3 scope fix must re-run it; README should note this |
| Docker + OAuth token | Root-owned `token_cache/` causes permission errors | `make setup` creates the directory as the host user before `docker compose run` writes it as root |
| Sonos SSDP in GitHub Actions CI | `soco.discovery.discover()` fires real multicast | All SSDP calls must be mocked at module level; `test_sonos_probe.py` does this correctly already |
| `network_mode: host` in `docker-compose.yml` | Works on Linux but fails on macOS/Windows Docker runners | Do not run `docker compose` in CI; use plain `pytest` instead |
| LRCLIB (lyrics cache SQLite) | SQLite file must exist before container mounts it | `make setup` / `touch lyrics_cache.db` must precede `docker compose up`; README documents this |

---

## Security Mistakes

Domain-specific security issues for this project.

| Mistake | Risk | Prevention |
|---------|------|------------|
| `.env` copied into Docker image (`COPY . .`, no `.dockerignore`) | Client ID + Secret extracted from image layers | Add `.dockerignore` with `.env` entry before public release |
| OAuth token in `token_cache/` copied into Docker image | Attacker gains `user-modify-playback-state` on real Spotify account | `.dockerignore` must include `token_cache/`; also verify with `docker run` test |
| Dashboard on `0.0.0.0:8888`, `network_mode: host`, no auth | Dashboard accessible by any LAN device with no login | Acceptable for home use; README must document this limitation explicitly |
| `POST /skip` endpoint has no authentication | Any LAN device can trigger skip | Acceptable for v1 scope; README should note it |
| Spotipy cache file world-readable if permissions not set | Other host users could read OAuth token | Token file is mode 600 (root-owned from container); acceptable |

---

## UX Pitfalls

Common user experience mistakes when open sourcing this type of project.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| README assumes Sonos present | Non-Sonos users give up at SSDP section | Clarify that Sonos is optional; service works with any Spotify Connect device |
| OAuth redirect "browser fails" not explained early | Users panic and abandon setup | Keep the explanation in Quick Start step 5 but add a callout box making it more visible |
| No CONTRIBUTING.md | Contributors don't know where to file issues or how to test | Add CONTRIBUTING.md in v1.6 documentation phase |
| Repo name `spotify-sentiment` vs. brand "Read the Room" | Confusing first impression on GitHub | Decide on canonical repo name; README should explain the rebrand |
| `.planning/` visible on GitHub | 313 internal planning files clutter repository; confuse contributors | Gitignore `.planning/` before first public push |
| `kids_present` profile name in UI without context | Users without kids unsure if profiles are customizable | README should list all four profile names and explain they are presets |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces for public release.

- [ ] **`.dockerignore` exists**: Does not exist — confirmed. `COPY . .` in Dockerfile copies `.env`, `token_cache/`, `state.json`, `lyrics_cache.db`, and `data/` into any Docker build. Verify fix: `ls .dockerignore` succeeds and `docker run --rm <image> cat /app/.env` fails.
- [ ] **`.planning/` removed from git tracking**: Currently 313 files tracked. Verify fix: `git ls-files .planning/` returns nothing.
- [ ] **`.claude/` removed from git tracking**: Currently 217 files tracked with absolute home directory paths. Verify fix: `git ls-files .claude/` returns nothing.
- [ ] **`192.168.1.164` removed from tests**: Appears in `tests/test_sonos_probe.py` as mock fixture IP. Verify fix: `grep -rn "192\.168\.1\.164" tests/ skip_client.py` returns nothing.
- [ ] **GitHub Actions CI workflow exists**: No `.github/workflows/` directory. Verify fix: `ls .github/workflows/*.yml` returns at least one file and the CI run passes.
- [ ] **LICENSE file exists**: Not present in tracked files. Verify fix: `ls LICENSE` succeeds.
- [ ] **CONTRIBUTING.md exists**: Not present. Verify fix: `ls CONTRIBUTING.md` succeeds.
- [ ] **CI passes with dummy env vars**: No real Spotify credentials should be needed. Verify fix: CI run on a branch with no GitHub secrets configured passes all tests.
- [ ] **OAuth scope mismatch documented**: Users who ran `make auth` before v1.3 must re-run it. Verify: README mentions this.
- [ ] **`state.json` not in git history**: Verify: `git log --all --oneline -- state.json` returns nothing.
- [ ] **`token_cache/.cache` not in git history**: Verify: `git log --all --oneline -- "token_cache/*"` returns nothing.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Spotify Client Secret committed to git history | HIGH | 1. Immediately rotate secret in Spotify Developer Dashboard. 2. Update `.env`. 3. Re-run `make auth`. 4. Use `git filter-repo` to purge commit. 5. Force-push to remote. 6. Notify any forks. |
| OAuth token committed to git history | HIGH | 1. Revoke in Spotify Account → Apps → Revoke Access. 2. Purge from history with `git filter-repo`. 3. Force-push. 4. Re-run `make auth` to get a new token. |
| `.env` baked into pushed Docker image | HIGH | 1. Delete image from registry immediately. 2. Rotate Spotify credentials. 3. Add `.dockerignore`. 4. Rebuild and push clean image. |
| Personal IP (`192.168.1.164`) in public tests | LOW | Push a single commit replacing with `192.168.1.100`. No security impact. |
| `.planning/` paths expose home username | LOW | `git rm -r --cached .planning/ && git commit`. Directories remain on disk. No secrets exposed. |
| CI fails on first push due to missing env | LOW | Add dummy env vars to workflow YAML. CI does not need real credentials for mocked tests. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| No `.dockerignore` — `.env` and tokens in Docker image | Repository hygiene audit | `docker run --rm <image> cat /app/.env` fails; `docker run --rm <image> ls /app/token_cache/` fails |
| `.planning/` absolute paths in public git | Repository hygiene audit | `git ls-files .planning/` returns nothing |
| `.claude/` directory in public git | Repository hygiene audit | `git ls-files .claude/` returns nothing |
| Personal IP `192.168.1.164` in tests | Source sanitization | `grep -rn "192\.168\.1\.164" tests/ skip_client.py` returns nothing |
| GitHub Actions CI missing | CI setup phase | `.github/workflows/ci.yml` exists and passes on push |
| CI fails without real Spotify credentials | CI setup phase | Workflow passes with dummy env vars, no GitHub secrets configured |
| LICENSE missing | License phase | `ls LICENSE` returns file; `head -1 LICENSE` shows chosen license |
| CONTRIBUTING.md missing | Documentation phase | `ls CONTRIBUTING.md` returns file |
| README written for author not strangers | README rewrite phase | A first-time reader can complete setup without asking questions |
| OAuth scope mismatch undocumented | README rewrite phase | README explains that existing users who ran `make auth` pre-v1.3 must re-run it |

---

## Sources

- Direct inspection of `/home/cgallarno/Development/spotify-sentiment/` repository (2026-04-06)
- `git ls-files`, `git check-ignore -v`, `git log --all --oneline` — all commands run against actual repo
- Confirmed: `.dockerignore` absent; `.env` present with real credentials; `token_cache/.cache` exists (551 bytes)
- Confirmed: `.planning/` (313 files) and `.claude/` (217 files) tracked by git with absolute `/home/cgallarno/` paths
- Confirmed: `192.168.1.164` in `tests/test_sonos_probe.py` (fixture mock values)
- Confirmed: `state.json` and `token_cache/.cache` correctly excluded from git via `.gitignore`
- Docker documentation on `COPY` instruction and `.dockerignore` behavior — HIGH confidence
- GitHub documentation on push protection and secret scanning — MEDIUM confidence

---
*Pitfalls research for: open sourcing a private Python/Docker home automation tool (Read the Room)*
*Researched: 2026-04-06*
