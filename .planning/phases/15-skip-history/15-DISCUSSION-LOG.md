# Phase 15: Skip History - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 15-skip-history
**Areas discussed:** SSE reconnect behavior, Event cap & ordering

---

## SSE Reconnect Behavior

### Reconnect strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep existing + fill gaps | On reconnect, fetch /feed, merge with DOM (deduplicate by ID), prepend missed events. No visual disruption. | ✓ |
| Clear and re-fetch | Wipe feed, re-populate from /feed. Simpler but causes visible flash/reset. | |
| Keep existing, no backfill | Keep DOM items, only show new events. Events during disconnect are silently lost. | |

**User's choice:** Keep existing + fill gaps
**Notes:** User prefers seamless reconnect with no visual disruption.

### Deduplication key

| Option | Description | Selected |
|--------|-------------|----------|
| timestamp + type | Match on event timestamp + type. Simple, works with existing shape. | |
| Add event IDs to events.jsonl | Daemon adds unique ID (UUID or monotonic counter) to each event line. More robust. | ✓ |

**User's choice:** Add event IDs to events.jsonl
**Notes:** User chose the more robust option despite requiring daemon-side changes. Event IDs future-proof dedup.

---

## Event Cap & Ordering

### Feed ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Newest on top | Most recent skip at top, matches current insertBefore behavior. | ✓ |
| Oldest on top | Chronological order, newest at bottom. More like traditional log. | |

**User's choice:** Newest on top
**Notes:** Consistent with existing feed rendering pattern.

### DOM cap

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 20, trim oldest | Bounded feed. Remove oldest when 21st arrives. Matches HIST-01 requirement. | ✓ |
| Uncapped, show all | Let feed grow indefinitely. No data lost from view. | |
| Cap at 50 | Higher cap, still bounded. | |

**User's choice:** Cap at 20, trim oldest
**Notes:** Aligns with HIST-01's "20 most recent" requirement. Prevents DOM bloat.

---

## Claude's Discretion

- Exact event ID implementation (monotonic counter vs UUID)
- Error handling for /feed endpoint
- Subtle hydration indicator vs silent population

## Deferred Ideas

None -- discussion stayed within phase scope
