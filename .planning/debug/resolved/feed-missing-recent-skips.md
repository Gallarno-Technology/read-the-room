---
status: resolved
trigger: "SSE-streamed skip events don't persist through a page refresh. After refreshing, the feed is missing the most recent skips."
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
---

## Current Focus

hypothesis: Browser caches GET /feed response because no Cache-Control header is set on the JSONResponse. On refresh, stale cached response is served.
test: Check if adding Cache-Control: no-store to /feed response fixes the issue
expecting: With no-cache header, browser always fetches fresh /feed data on refresh
next_action: Add Cache-Control header to /feed endpoint

## Symptoms

expected: After page refresh, skip feed shows all recent skips including ones that arrived via SSE before the refresh
actual: SSE events disappear on refresh; feed is missing the most recent skips
errors: No error messages reported — feed just shows stale/incomplete data
reproduction: Let skip events stream in via SSE, then refresh the page. Recent events are gone.
started: After Phase 15 (skip history) deployment

## Eliminated

## Evidence

- timestamp: 2026-04-04T21:36
  checked: File I/O between daemon and web_ui containers
  found: Cross-container writes via bind mount are immediately visible to readers. Simulated write+read tests all pass.
  implication: The bug is NOT in file I/O or Docker bind mount visibility.

- timestamp: 2026-04-04T21:38
  checked: GET /feed response headers
  found: Response has NO Cache-Control header. Headers are: date, server, content-length, content-type only.
  implication: Browser may cache the /feed response. On refresh, stale cached response is served instead of fresh data.

- timestamp: 2026-04-04T21:38
  checked: /feed endpoint logic
  found: Reads full file, filters correctly for skip/five_skip_warning, returns newest-first. Logic is correct.
  implication: Backend returns correct data when actually called. Issue is browser not calling it fresh.

- timestamp: 2026-04-04T21:38
  checked: _file_tail() partial read issue
  found: Log shows "skipping malformed event line: 'id\": 123}'" confirming partial reads can occur
  implication: _file_tail can lose SSE events on partial reads, but this is a separate issue from the /feed bug

## Resolution

root_cause: GET /feed and GET /now-playing responses lack Cache-Control headers. Browsers apply heuristic caching to fetch() sub-requests (cache mode "default"). On soft refresh (F5/Ctrl+R), the browser may serve a stale cached /feed response instead of requesting fresh data. SSE events arrive live (not cached), so the user sees events in real-time but loses them on refresh because the /feed hydration returns stale data. Additionally, _append_event() doesn't call f.flush() which can cause _file_tail() partial reads (secondary issue).
fix: Add Cache-Control: no-store headers to /feed and /now-playing responses. Add f.flush() to _append_event() to ensure writes are immediately visible.
verification: Rebuilt and restarted containers. Confirmed Cache-Control: no-store header present on GET /feed and GET /now-playing responses via curl. Feed still returns correct 20 events newest-first.
files_changed: [web_ui/main.py, daemon.py]
