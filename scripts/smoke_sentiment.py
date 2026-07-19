#!/usr/bin/env python3
"""Real-key smoke test for the v1.9 LLM sentiment pipeline.

Runs a few calibration anchors through the ACTUAL SentimentService (live Claude
API) with real lyrics fetched via the production LyricsService, prints each
per-category analysis plus the code-derived Family Friendly / Mixed Company /
Close Friends verdicts and latency, then checks a handful of must-hold
expectations. This makes a real API call per anchor — costs a few cents.

It exercises the real path end-to-end minus Spotify: LyricsService (LRCLIB) →
SentimentService → AnthropicProvider → Claude → SongAnalysis → derive_verdict.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... python scripts/smoke_sentiment.py
    # or put ANTHROPIC_API_KEY in .env (loaded automatically)

Exit code 0 if every evaluated anchor met its must-hold checks, 1 otherwise.
Anchors whose lyrics can't be fetched are reported as SKIPPED (infra), not failed.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Allow running as `python scripts/smoke_sentiment.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from lyrics_service import LyricsService  # noqa: E402
from profiles import PROFILES, derive_verdict  # noqa: E402
from sentiment_service import CATEGORY_NAMES, SentimentService  # noqa: E402

# Each anchor: real title/artist + the checks that must hold. Checks are kept
# robust to normal model variance (severity buckets / verdict on the clear cases).
ANCHORS = [
    {
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "note": "clean baseline — should pass every profile",
        "expect_verdicts": {"family_friendly": "pass", "mixed_company": "pass", "close_friends": "pass"},
    },
    {
        "title": "Pumped Up Kicks",
        "artist": "Foster the People",
        "note": "clean-sounding lyrics, first-person school-shooter POV — the LLM's whole reason for existing",
        "expect_category_in": ("violence", {"narrative", "graphic"}),
        "expect_verdicts": {"family_friendly": "decline"},
    },
    {
        "title": "Semi-Charmed Life",
        "artist": "Third Eye Blind",
        "note": "hard-drug content with cautionary framing — framing axis should let it pass Mixed Company",
        "expect_category_nonzero": "drug_references",
    },
]

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower())


def _print_analysis(analysis) -> None:
    print(f"  confidence={analysis.confidence}  framing={analysis.framing}  model={analysis.model_id}")
    for name in CATEGORY_NAMES:
        cat = analysis.category(name)
        reason = f"  {DIM}{cat.reason}{RESET}" if cat.reason else ""
        mark = "" if cat.severity == "none" else "•"
        print(f"    {mark:1} {name:16} {cat.severity}{reason}")
    verdicts = {p: derive_verdict(analysis, p) for p in PROFILES}
    rendered = "  ".join(
        f"{p}={GREEN if v == 'pass' else RED}{v}{RESET}" for p, v in verdicts.items()
    )
    print(f"  verdicts: {rendered}")
    if analysis.summary:
        print(f"  {DIM}{analysis.summary}{RESET}")


def _check(anchor: dict, analysis) -> list[str]:
    """Return a list of failure messages ([] means all must-holds passed)."""
    fails: list[str] = []
    verdicts = {p: derive_verdict(analysis, p) for p in PROFILES}

    for profile, expected in anchor.get("expect_verdicts", {}).items():
        if verdicts[profile] != expected:
            fails.append(f"{profile} expected {expected}, got {verdicts[profile]}")

    if "expect_category_in" in anchor:
        name, allowed = anchor["expect_category_in"]
        got = analysis.category(name).severity
        if got not in allowed:
            fails.append(f"{name} expected one of {sorted(allowed)}, got {got!r}")

    if "expect_category_nonzero" in anchor:
        name = anchor["expect_category_nonzero"]
        got = analysis.category(name).severity
        if got == "none":
            fails.append(f"{name} expected non-none, got 'none'")

    return fails


async def run() -> int:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{RED}ANTHROPIC_API_KEY not set{RESET} — export it or add it to .env, then re-run.")
        return 2

    db_path = os.environ.get("LYRICS_DB_PATH", "lyrics_cache.db")
    model = os.environ.get("SENTIMENT_MODEL", "claude-haiku-4-5-20251001")
    lyrics = LyricsService(db_path=db_path)
    service = SentimentService(model=model)

    print(f"Model: {model}   lyrics db: {db_path}")
    print(f"{DIM}Rubric prompt-caching is enabled; the 2nd+ calls bill the rubric at the cached-read rate.{RESET}\n")

    evaluated = 0
    failed_anchors = 0
    skipped = 0
    total_latency = 0.0

    for anchor in ANCHORS:
        title, artist = anchor["title"], anchor["artist"]
        print(f"── {title} — {artist}")
        print(f"   {DIM}{anchor['note']}{RESET}")

        lr = await lyrics.get_lyrics(
            track_id=f"smoke:{_slug(title)}", track_name=title, artist_name=artist
        )
        if lr.instrumental or not lr.lyrics:
            reason = "instrumental" if lr.instrumental else "no lyrics from LRCLIB"
            print(f"   {YELLOW}SKIPPED{RESET} — {reason}\n")
            skipped += 1
            continue

        t0 = time.monotonic()
        analysis = await service.evaluate(f"smoke:{_slug(title)}", title, artist, lr.lyrics)
        dt = time.monotonic() - t0
        total_latency += dt

        if analysis is None:
            print(f"   {RED}FAILED{RESET} — evaluate() returned None (API error or no tool_use)\n")
            failed_anchors += 1
            evaluated += 1
            continue

        evaluated += 1
        print(f"  latency={dt:.1f}s  ({len(lr.lyrics)} chars of lyrics)")
        _print_analysis(analysis)

        fails = _check(anchor, analysis)
        if fails:
            failed_anchors += 1
            print(f"  {RED}CHECK FAILED{RESET}: " + "; ".join(fails))
        else:
            print(f"  {GREEN}checks passed{RESET}")
        print()

    await lyrics.close()

    print("═" * 60)
    print(
        f"evaluated={evaluated}  passed={evaluated - failed_anchors}  "
        f"failed={failed_anchors}  skipped={skipped}  "
        f"mean_latency={(total_latency / evaluated):.1f}s" if evaluated else
        f"evaluated=0  skipped={skipped}"
    )
    return 1 if failed_anchors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
