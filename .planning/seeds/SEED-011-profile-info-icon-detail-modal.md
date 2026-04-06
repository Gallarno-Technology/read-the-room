---
id: SEED-011
status: dormant
planted: 2026-04-05
planted_during: v1.4 — Dashboard Polish & Filter Profiles
trigger_when: when a milestone focuses on dashboard UX or onboarding
scope: Small
---

# SEED-011: Info icon showing per-profile skip details

## Why This Matters

Users currently pick a filter profile by name alone ("Kids Present",
"Above The Covers", etc.) with no in-context explanation of what each one
actually skips. This causes two problems:

1. **Discoverability** — users don't know what they're getting without trial
   and error or reading external docs.
2. **Trust / transparency** — parents especially want to know *exactly* what
   will and won't be filtered before committing to a profile for a family
   listening session.

An info icon (ⓘ) next to each profile in the dropdown, tapped/clicked to
reveal a compact breakdown, solves both without cluttering the UI.

## When to Surface

**Trigger:** When a milestone focuses on dashboard UX or onboarding

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Dashboard UX improvements, polish, or onboarding work
- Any milestone that touches the profile selector or profile management
- A "public release / first impressions" milestone where transparency matters

## Scope Estimate

**Small** — A few hours. Concretely:
- Add ⓘ icon element next to each `.profile-option` in `index.html`
- On tap/click, show a small popover or modal listing what the profile scans
  (profanity, drug refs, sexual content, explicit flag, severity threshold)
- Content can be static strings derived directly from `PROFILE_MAP` in `daemon.py`
- No backend changes needed — all four profiles and their flags are already
  defined and stable

## Breadcrumbs

Related code and decisions found in the current codebase:

- `daemon.py:51-84` — `PROFILE_MAP` dict defines all four profiles and their
  flags (`explicit_skip`, `min_severity`, `drug`, `sexual`, `profanity`,
  `lyrics`). This is the source of truth for what to show in the detail view.
- `web_ui/templates/index.html:454-458` — profile dropdown markup with
  `.profile-option` divs; info icon and popover would be added here
- `web_ui/templates/index.html:225-261` — profile CSS; new tooltip/popover
  styles go here
- `web_ui/main.py:237` — `VALID_PROFILES` frozenset; confirms the four profile
  keys in use

## Notes

The detail view content maps naturally from `PROFILE_MAP` flags:
- `profanity: True` → "Skips tracks with profanity"
- `drug: True` → "Skips tracks with drug references"
- `sexual: True` → "Skips tracks with sexual content"
- `explicit_skip: True` → "Skips Spotify-marked explicit tracks"
- `lyrics: False` → "Works without lyrics (title/artist scan only)"

Static strings per profile are fine for the small scope — no need to
dynamically derive them from the Python config at runtime.
