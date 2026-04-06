# Phase 18: Profile Info Icon - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-06
**Phase:** 18-profile-info-icon
**Mode:** discuss
**Areas discussed:** Reveal mechanism, Info content format, Icon placement

---

## Gray Areas Presented

- Reveal mechanism — tooltip, popover flyout, or inline expansion
- Info content format — checkmarks, full grid, or plain sentence; profile name header?
- Icon placement — right of split button, top-right corner of card, or below button

## Discussion

### Reveal Mechanism

**Q:** How should tapping ⓘ show the profile info?
**Options:** Popover flyout, Inline expansion, CSS tooltip (hover only)
**Selected:** Popover flyout (Recommended)
**User note:** "on a mobile device can it be a bottom sheet? on a wider screen with a popover?"

**Q:** Responsive reveal: popover on desktop, bottom sheet on mobile?
**Options:** Yes — responsive, No — popover only
**Selected:** Yes — responsive (≤640px → bottom sheet, >640px → popover)

### Info Content Format

**Q:** What should the breakdown show for enabled rules?
**Options:** Checkmarks only, Full grid on/off for all, Plain sentence
**Selected:** Plain sentence

**Q:** Does the popover/sheet show the profile name as a header above the sentence?
**Options:** Yes — name + sentence, Sentence only
**Selected:** Yes — name + sentence

### Icon Placement

**Q:** Where on the FSM card should ⓘ live?
**Options:** Right of split button, Top-right corner of card, Below the button
**Selected:** Top-right corner of card (absolutely positioned)

---

## Corrections / Deferred Ideas

None — all selections were user choices; no corrections needed.
