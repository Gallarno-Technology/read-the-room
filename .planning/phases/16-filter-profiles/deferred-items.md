# Deferred Items — Phase 16

## Pre-Existing Test Failure (Out of Scope)

**File:** `tests/test_skip_client.py::test_soco_pause_uses_cached_ip`
**Discovered during:** Plan 16-03, Task 2 verification
**Status:** Pre-existing failure — confirmed failing BEFORE any plan 16-03 changes via `git stash`
**Error:** `AssertionError: Expected 'pause' to have been called once. Called 0 times.`
**Cause:** `SocoSkipClient.pause()` method does not call `speaker.pause()` as the test expects. Likely a gap in the SoCo skip client implementation.
**Impact:** Unrelated to Phase 16 filter profiles changes (HTML/CSS/JS only in plan 16-03; Python backend in 16-01 and 16-02).
**Deferred to:** Future fix sprint — SoCo skip client behavior.
