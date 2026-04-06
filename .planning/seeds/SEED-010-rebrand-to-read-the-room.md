---
id: SEED-010
status: dormant
planted: 2026-04-05
planted_during: v1.4 — Dashboard Polish & Filter Profiles
trigger_when: next milestone
scope: Small
---

# SEED-010: Rebrand to "Read the Room"

## Why This Matters

The current name "spotify-sentiment" is a dev-era placeholder — accurate but
flat. "Read the Room" is more evocative, marketable, and hints at the broader
vision: a tool that understands the vibe of music playing in shared spaces, not
just a Spotify filter script.

The rebrand also signals that the product's scope can grow beyond family safe
mode — other listening contexts, other platforms, other room-awareness use cases.

## When to Surface

**Trigger:** Next milestone (v1.5 or beyond)

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- The milestone adds features beyond content filtering (e.g., platform support, discovery, social)
- The milestone is a polish / release-prep milestone where branding matters
- Any milestone that involves a README overhaul, landing page, or public-facing docs

## Scope Estimate

**Small** — A few hours. Concretely:
- Rename directory / repo from `spotify-sentiment` → `read-the-room` (or keep dir, update display name)
- Update `README.md` title and description
- Update any in-code strings that reference the old name (daemon service name, log labels, etc.)
- Update `.planning/PROJECT.md` project name field
- Optional: update `pyproject.toml` or `setup.cfg` package name if added by then

## Breadcrumbs

Related code and decisions found in the current codebase:

- `README.md` — top-level project description; primary rebrand target
- `daemon.py` — service name / log labels likely reference current project name
- `.planning/PROJECT.md` — project name field at top of file
- Directory name: `/home/cgallarno/Development/spotify-sentiment/` — rename candidate

## Notes

The name "Read the Room" was proposed during v1.4 milestone work. No code
changes needed to plant this seed — it's purely a naming/branding decision
that becomes meaningful when the project is ready for a wider audience.
