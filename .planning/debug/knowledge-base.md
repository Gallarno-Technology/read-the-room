# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## feed-missing-recent-skips — SSE events disappear on page refresh due to browser caching stale /feed response
- **Date:** 2026-04-04
- **Error patterns:** feed missing recent skips, stale data on refresh, SSE events disappear, Cache-Control, heuristic caching, partial read, flush
- **Root cause:** GET /feed and GET /now-playing responses lacked Cache-Control headers. Browsers applied heuristic caching to fetch() sub-requests, serving stale cached responses on refresh instead of fetching fresh data. Secondary issue: _append_event() missing f.flush() causing partial reads.
- **Fix:** Added Cache-Control: no-store headers to /feed and /now-playing JSONResponse. Added f.flush() after event file writes.
- **Files changed:** web_ui/main.py, daemon.py
---
