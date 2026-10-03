#!/usr/bin/env python3
"""Seed the golden set from a fixtures CSV (rtr-test-fixtures.csv format).

Reads the Song / Artist / "<Profile> Expected" / Notes columns and upserts each
row into the golden_set table (matched by normalized song + artist, so re-running
is safe and updates existing rows). "Threshold Dependent" becomes 'either' —
the profile's verdict isn't asserted for that song.

Usage (in prod, from the LXC):
    docker compose exec -T web_ui python scripts/seed_golden_set.py rtr-test-fixtures.csv
    # or locally:
    FEEDBACK_DB_PATH=data/feedback.db python scripts/seed_golden_set.py rtr-test-fixtures.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow running as `python scripts/seed_golden_set.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feedback_store import FEEDBACK_DB_PATH, FeedbackStore  # noqa: E402

COLUMNS = {
    "family_friendly": "Family Friendly Expected",
    "mixed_company": "Mixed Company Expected",
    "close_friends": "Close Friends Expected",
}
VALUE_MAP = {"pass": "pass", "decline": "decline", "threshold dependent": "either", "either": "either"}


def parse_expected(row: dict) -> dict[str, str]:
    expected = {}
    for profile, col in COLUMNS.items():
        raw = (row.get(col) or "").strip().lower()
        if raw not in VALUE_MAP:
            raise ValueError(f"{row.get('Song')!r}: unrecognized {col} value {row.get(col)!r}")
        expected[profile] = VALUE_MAP[raw]
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv_path")
    parser.add_argument("--db", default=FEEDBACK_DB_PATH, help=f"default: {FEEDBACK_DB_PATH}")
    args = parser.parse_args()

    store = FeedbackStore(args.db)
    count = 0
    with open(args.csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if not (row.get("Song") or "").strip():
                continue
            store.upsert_golden(
                track=row["Song"].strip(),
                artist=row["Artist"].strip(),
                expected=parse_expected(row),
                notes=(row.get("Notes") or "").strip(),
                source="fixture",
            )
            count += 1
    print(f"Seeded {count} golden-set rows into {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
