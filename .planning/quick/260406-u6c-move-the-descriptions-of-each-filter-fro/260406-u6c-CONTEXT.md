# Quick Task 260406-u6c: Move filter descriptions to dropdown, repurpose info icon as app overview — Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Task Boundary

Two changes to `web_ui/templates/index.html`:

1. **Dropdown** — Move the per-profile descriptions (currently the prose sentences in the `PROFILE_INFO` JS map, shown in the info icon popout) to appear beneath each profile option in the `#profile-dropdown` menu.

2. **Info icon popout** — Replace the per-profile breakdown content with a short app overview: fixed copy regardless of which profile is active.

</domain>

<decisions>
## Implementation Decisions

### Info icon overview content
The popout heading and body are fully specified by the user:

- **Heading:** "Read the Room"
- **Body (exact copy, 3 paragraphs separated by line breaks):**
  - "Your music doesn't change. The filter does."
  - "Set your House Rules for who's in the room. Read the Room handles the rest — quietly, in the background, without making a scene."
  - "Your house. Your standards."

### Dropdown description style
Claude's discretion — add a secondary descriptive line beneath each profile option name inside the dropdown, matching the existing UI style (no separate query from user; keep it visually consistent with current dropdown layout).

### Info icon UI format
Keep the existing popout structure (heading + body). Replace dynamic PROFILE_INFO content with the static copy above. The live-update hook inside `setFsmUI()` (which re-renders the panel on profile change) should be removed or made a no-op since the content is now static and profile-agnostic.

</decisions>

<specifics>
## Specific Ideas

Exact copy for the info popout body:

> Your music doesn't change. The filter does.
>
> Set your House Rules for who's in the room. Read the Room handles the rest — quietly, in the background, without making a scene.
>
> Your house. Your standards.

The per-profile prose sentences currently in `PROFILE_INFO` map (e.g., "Skips profanity, drug references, sexual content, and explicit-flagged tracks.") should move to the dropdown as a subtitle under each profile name. The four profiles and their current descriptions are:

- **Kids Present** — "Skips profanity, drug references, sexual content, and explicit-flagged tracks."
- **Were All Adults** — (check current PROFILE_INFO map for exact sentence)
- **Above The Covers** — (check current PROFILE_INFO map for exact sentence)
- **Permissive** — "Skips explicit-flagged tracks."

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.
</canonical_refs>
