# Deferred Items — Phase 14

## Pre-existing Test Failures (Out of Scope)

- `tests/test_skip_client.py::test_soco_pause_uses_cached_ip` — mock.pause not called; likely SocoSkipClient.pause implementation changed
- `tests/test_skip_client.py::test_soco_pause_falls_back_to_discovery_when_not_cached` — same issue
