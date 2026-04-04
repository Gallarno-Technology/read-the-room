# Phase 13: Dashboard Badge Variants - Context

**Gathered:** 2026-04-04 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Add CSS badge classes and JS detection logic so that skip feed entries for drug-reference and sexual-content skips display visually distinct badges. Changes are confined to `web_ui/templates/index.html` — CSS additions and updates to `setBadgeClass`/`badgeLabel` functions. No backend changes, no scanner changes, no now-playing card changes.

</domain>

<decisions>
## Implementation Decisions

### Badge Detection Logic
- **D-01:** Extend `setBadgeClass(reason)` with two new branches: `r.includes('drug')` → `'badge--drug-reference'` and `r.includes('sexual')` → `'badge--sexual-content'`. Add matching branches to `badgeLabel(reason)` returning `'Drug reference'` and `'Sexual content'` respectively.
- **D-02:** Detection uses the `evt.reason` string field (authoritative skip reason), not the boolean fields. Pre-v1.3 events have `reason` values like `"profanity"` or `"explicit"` — neither matches the new patterns, so backwards compatibility is implicit.
- **D-03:** New branches slot in before the default fallback in `setBadgeClass` — order: explicit → profanity → drug → sexual → adult → fallback. Same in `badgeLabel`.

### CSS Badge Colors
- **D-04:** `badge--drug-reference`: purple — `background: rgba(130, 80, 190, 0.2)`, `color: #a878d4`, `border-color: rgba(130, 80, 190, 0.3)`. Purple is absent from the existing palette and immediately distinguishable.
- **D-05:** `badge--sexual-content`: pink/magenta — `background: rgba(190, 80, 140, 0.2)`, `color: #d478a8`, `border-color: rgba(190, 80, 140, 0.3)`. Pink is absent from the existing palette and clearly distinct from purple.
- **D-06:** Both new classes follow the exact same structure as existing badge classes (rgba background at 0.2, color at lightened hex, border at 0.3). No deviations from the established pattern.

### Badge Label Text
- **D-07:** Drug reference badge text: `'Drug reference'` — matches success criteria SC-01 exactly.
- **D-08:** Sexual content badge text: `'Sexual content'` — matches success criteria SC-02 exactly.

### Backwards Compatibility
- **D-09:** No explicit guard needed for pre-v1.3 events. The `setBadgeClass`/`badgeLabel` functions already default to `'badge--explicit'` / `'Flagged: explicit tag'` for unknown reasons — pre-v1.3 `"profanity"` and `"explicit"` reasons continue to match their existing branches before reaching the new ones. Dashboard loads without JS errors (SC-04 satisfied by existing string-fallback pattern).

### Scope Boundary (out of scope)
- **D-10:** Drug/sexual badges on the now-playing eval card are explicitly out of scope (REQUIREMENTS.md Out of Scope: "Drug/sexual badges on now-playing eval card"). `setEvalBadge` is not modified.
- **D-11:** The `drug_reference` and `sexual_content` boolean fields on SSE `eval_result` events are not read by the frontend in this phase — only `evt.reason` on skip events is used.

### Claude's Discretion
- Exact placement of new badge CSS (append after `badge--fsm-off` at end of badge block)
- Whether to add a JS comment grouping the new branches

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §UI-01 — single dashboard requirement for this phase
- `.planning/REQUIREMENTS.md` §Out of Scope — "Drug/sexual badges on now-playing eval card" is explicitly excluded

### Source file to modify
- `web_ui/templates/index.html` — the only file that changes in this phase; contains all CSS and JS inline

### Content signals reference
- `content_checker.py` lines 136–140 — the four `reason` values: `"profanity"`, `"drug_reference"`, `"sexual_content"`, `"clean"` (confirms exact strings to match in `setBadgeClass`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `setBadgeClass(reason)` (index.html ~line 441) — string-match function that maps `reason` text to CSS class; extend with two new branches
- `badgeLabel(reason)` (index.html ~line 449) — parallel label function; extend with matching branches
- Existing badge CSS classes (`badge--explicit`, `badge--profanity`, etc.) — follow same `rgba()` color structure for new classes

### Established Patterns
- All badge CSS follows: `background: rgba(R, G, B, 0.2)`, `color: #RRGGBB` (lightened hex), `border-color: rgba(R, G, B, 0.3)`
- `setBadgeClass` uses `r.includes('{keyword}')` against `reason.toLowerCase()` — consistent with new `'drug'` and `'sexual'` keywords
- `prependSkipItem(evt)` creates one badge per skip item using `setBadgeClass(evt.reason)` — no structural change needed

### Integration Points
- `prependSkipItem` reads `evt.reason` from SSE `skip` events — daemon writes `result.reason` which is `"drug_reference"` or `"sexual_content"` for the new signal skips (confirmed in `daemon.py` line 371)
- Skip feed `<li>` uses flex layout with `gap: 4px` — a single badge renders correctly without structural changes

</code_context>

<specifics>
## Specific Ideas

- Success criteria specify exact badge text: "Drug reference" and "Sexual content" — use these strings verbatim, no "Flagged:" prefix
- The existing badge pattern uses "Flagged: explicit tag" / "Flagged: strong language" for skip feed, but success criteria override — use plain category names for the new signals

</specifics>

<deferred>
## Deferred Ideas

- Per-category toggle UI (TOGL-01, TOGL-02) — v2+, different phase
- Multi-badge display in skip feed if multiple signals fire simultaneously — not required by any current success criterion; skip feed shows one reason per skip

None — analysis stayed within phase scope.

</deferred>

---

*Phase: 13-dashboard-badge-variants*
*Context gathered: 2026-04-04*
