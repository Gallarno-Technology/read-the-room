---
id: SEED-009
status: dormant
planted: 2026-04-04
planted_during: v1.4 Dashboard Polish & Filter Profiles (milestone start)
trigger_when: when adding push notifications, SMS, or Telegram integration
scope: medium
---

# SEED-009: Notify when a song is implicitly allowed with no lyrics — request manual review

## Why This Matters

When LRCLIB can't return lyrics for a track, `content_checker.py` falls back to scanning the
title + artist. If that scan is clean, the song is allowed with `reason=lyrics_unavailable`.
It plays — which is the right safe default — but the parent is never told the song wasn't
fully vetted. It may have lyrics the system simply couldn't see.

Right now the dashboard shows a `no-lyrics` eval_state badge on the now-playing card, but
it's passive. There's no prompt to review, no way to flag the track as "I've heard this, it's
fine" or "this needs to be blocked", and no record of unvetted-but-allowed tracks over time.

A notification (push / SMS / Telegram) when an unvetted track plays — with a one-tap
approve/flag action — closes this gap without adding friction to normal listening.

## When to Surface

**Trigger:** When adding push notifications, SMS, or Telegram integration to the app.

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches
any of these conditions:
- Milestone adds outbound notification capabilities (Telegram bot, SMS, push)
- Milestone adds a manual review queue or parent-approval workflow
- Milestone adds an audit trail for allowed-but-unverified tracks

## Scope Estimate

**Medium** — A phase or two. Likely decomposition:
1. Backend: track `lyrics_unavailable + allow` events separately (already in events.jsonl);
   expose a `GET /review-queue` endpoint returning unreviewed no-lyrics tracks
2. Notification: when a no-lyrics track is allowed, emit notification via the configured
   channel (Telegram/SMS/push) with track name, artist, and approve/flag action links
3. Review action: `POST /review/{track_id}` to mark a track safe or blocked; blocked tracks
   added to a local denylist so they skip in the future even without lyrics

## Breadcrumbs

- `content_checker.py:137` — `title_action, title_reason = "allow", "lyrics_unavailable"` — the exact allow path this seed addresses
- `content_checker.py:33` — `reason` field comment lists `lyrics_unavailable` and `no_lyrics_service` as distinct cases
- `daemon.py:197` — maps `reason in ("lyrics_unavailable", "no_lyrics_service")` → `eval_state="no-lyrics"` — the canonical state string
- `web_ui/templates/index.html` — dashboard already renders `no-lyrics` eval_state badge; passive indicator already exists
- `daemon.py:95` — daemon appends to `events.jsonl` on every track; `lyrics_unavailable` events are already logged there
- `lyrics_service.py:50` — `instrumental` flag: instrumental tracks intentionally have no lyrics — review queue should exclude these

## Notes

Two distinct `reason` values cover the no-lyrics scenario:
- `lyrics_unavailable` — LRCLIB returned no lyrics, title scan ran, track was clean enough to allow
- `no_lyrics_service` — lyrics pipeline not configured or failed entirely; allowed with zero scanning

The review notification should target `lyrics_unavailable` only — `no_lyrics_service` means
the pipeline isn't running at all (infra issue), which is a different class of problem.

The approve/flag action model is the interesting design question: a one-tap Telegram inline
keyboard button is the lowest-friction UX. Approved tracks could be cached in a local
`reviewed_safe.json`; flagged tracks added to a `denylist.json` that `content_checker.py`
checks before the LRCLIB fetch.
