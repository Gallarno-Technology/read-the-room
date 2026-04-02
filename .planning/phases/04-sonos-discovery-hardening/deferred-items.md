# Deferred Items — Phase 04 sonos-discovery-hardening

## Pre-existing Test Failures (Out of Scope for Plan 04-01)

**Discovered during:** Plan 04-01, Task 2 verification
**Tests affected:**
- `tests/test_skip_client.py::test_soco_pause_uses_cached_ip`
- `tests/test_skip_client.py::test_soco_pause_falls_back_to_discovery_when_not_cached`

**Symptom:** `mock_speaker.pause.assert_called_once()` fails — `pause` was called 0 times.

**Root cause (likely):** `SocoSkipClient.pause()` implementation calls `speaker.pause()` but the mock patch targets `soco.SoCo` rather than the actual `soco.SoCo()` instance created inside the method. The mock is not being threaded through `run_in_executor` correctly, or the pause method name conflicts with a MagicMock auto-attribute.

**Status:** Pre-existing before this phase. Not introduced by Plan 04-01 changes.

**Action needed:** Fix in a future plan or as part of Plan 04-02 if it touches `skip_client.py` pause behavior.
