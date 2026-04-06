# Phase 16: Filter Profiles - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 16-filter-profiles
**Areas discussed:** Profile selector widget, FSM-off behavior

---

## Profile selector widget

| Option | Description | Selected |
|--------|-------------|----------|
| 4 stacked buttons | Each profile is a button — one highlighted as active | |
| Dropdown / select | Single select element, compact one-line | ✓ |
| Radio buttons | Classic HTML radio group | |
| Horizontal tab row | 4 tabs in a row, active tab underlined | |

**User's choice:** Dropdown, with a specific design twist: the active profile name replaces "The Library is Open" text on the FSM button. The right side of the button (▾ icon area) triggers the dropdown. Left side still toggles FSM.

**Follow-up — Dropdown implementation:**

| Option | Description | Selected |
|--------|-------------|----------|
| Custom CSS dropdown | Styled to match dashboard — dark bg, Courier Prime | ✓ |
| Native `<select>` | Browser-native, no styling | |
| Overlay button list | Absolutely-positioned list of 4 buttons | |

**Follow-up — Dropdown position:**

| Option | Selected |
|--------|----------|
| Below the button | ✓ |
| Above the button | |

**Follow-up — Profile on FSM re-enable:**

| Option | Selected |
|--------|----------|
| Last-used profile | ✓ |
| Always Family Friendly | |

---

## FSM-off behavior

| Option | Description | Selected |
|--------|-------------|----------|
| No ▾ when FSM off | Button is single-action toggle when closed | |
| Show ▾ but disabled | Icon visible, clicking does nothing when off | |
| Show ▾ and allow pre-selecting | Parent can change profile while FSM off | ✓ |

**User's choice:** Allow pre-selecting while FSM is off — parent can queue up a profile before enabling filtering.

**Follow-up — Button text after pre-selecting while FSM off:**

| Option | Selected |
|--------|----------|
| 'The Library is Closed' still | |
| Show selected profile name | ✓ |

**Notes:** Button shows profile name in grey/fsm-off styling when FSM is off. Visual state (gold vs grey) communicates FSM on/off, text communicates which profile is active/queued.

**Follow-up — Checkmark when FSM off:**

| Option | Selected |
|--------|----------|
| Yes — show checkmark on pre-selected profile | ✓ |
| No checkmark when FSM off | |

---

## Claude's Discretion

- Exact CSS for split-button divider between toggle zone and ▾ zone
- Dropdown animation (fade-in vs instant)
- ContentChecker profile application approach (reconstruct on change vs other)
- `POST /profile` endpoint shape
- Web UI initial profile state injection pattern

## Deferred Ideas

None.
