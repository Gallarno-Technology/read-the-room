---
status: partial
phase: 16-filter-profiles
source: [16-VERIFICATION.md]
started: 2026-04-05T00:00:00Z
updated: 2026-04-05T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual rendering
expected: Button layout correct — left zone shows profile name, right zone shows ▾; gold background + dark text when FSM on; grey background + normal text when FSM off; font inherits correctly (no blue text)
result: [pending]

### 2. Click zone independence
expected: Right zone opens dropdown only (FSM state unchanged); left zone toggles FSM only (dropdown does not open)
result: [pending]

### 3. Profile selection end-to-end
expected: Clicking a profile option updates label optimistically, closes dropdown, POSTs to /profile, persists in state.json, FSM state unchanged
result: [pending]

### 4. Dropdown dismiss
expected: Clicking outside the dropdown closes it; pressing Escape closes it; neither changes FSM or profile selection
result: [pending]

### 5. SSE reconnect
expected: When the SSE stream reconnects, any open dropdown auto-closes
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
