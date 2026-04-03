# Phase 8: Dashboard Frontend - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-03
**Phase:** 08-dashboard-frontend
**Mode:** assumptions
**Areas analyzed:** Card Layout, Page-Load Hydration, Eval-State Badge, Skip Button

## Assumptions Presented

### Now-Playing Card Placement and Layout
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Card inserted between FSM toggle and Incident Log | Likely | `index.html` two-card layout; action → history hierarchy |

Alternatives presented:
- Top of page (above FSM toggle)
- Bottom of page (below Incident Log)

### Page-Load Hydration Strategy
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| DOMContentLoaded fetch + SSE onopen re-fetch; no polling | Confident | `07-CONTEXT.md D-03` explicit; NOW-04/05 requirements |

### Eval-State Badge Rendering
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New CSS modifier classes alongside existing feed badge classes | Likely | Existing badge pattern in `index.html`; 6 distinct eval_state strings from `06-CONTEXT.md D-02` |

Alternatives presented:
- Reuse existing badge classes by mapping eval_state → closest existing class

### Skip Button Disabled-State
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Native `button.disabled` + inline error mirroring `#fsm-error` | Confident | SKIP-04 explicit; `#fsm-error` is the only error UI pattern in the file |

## Corrections Made

No corrections — all assumptions confirmed (user selected recommended options for both Likely items).

## External Research

None — event schemas, API contracts, idle sentinel, track_id guard behavior, and all UI patterns fully specified in prior phase CONTEXT files and existing `index.html`.
