#!/usr/bin/env python3
"""Read the Room — listener feedback + golden set store.

Two tables in one SQLite file (FEEDBACK_DB_PATH, default data/feedback.db —
the data/ volume both containers share):

  feedback    — one row per listener signal, snapshotting everything needed to
                review it later: the profile that was active, the LLM's full
                per-category analysis, its summary, rubric version and model.
                kind = 'wrong_skip'  (👎 on an auto-skip: "this shouldn't have skipped")
                     | 'manual_skip' (listener skipped from the app: "maybe this should have")
                status = 'pending' → 'promoted' | 'dismissed'

  golden_set  — known-borderline songs with the expected verdict per profile
                ('pass' | 'decline' | 'either'), the regression list prompt
                revisions are A/B tested against. Keyed by normalized
                (track, artist) so the rtr-test-fixtures.csv seeds (which have no
                Spotify id) and promoted feedback merge into one list.

Synchronous sqlite3 on purpose: every operation is a single small statement on
a household-sized table, called from the web UI's request handlers.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
from typing import Any

from profiles import PROFILES, derive_verdict
from sentiment_service import CATEGORY_NAMES, CategoryRating, SongAnalysis

FEEDBACK_DB_PATH = os.environ.get("FEEDBACK_DB_PATH", "data/feedback.db")

FEEDBACK_KINDS = ("wrong_skip", "manual_skip")
FEEDBACK_STATUSES = ("pending", "promoted", "dismissed")
EXPECTED_VALUES = ("pass", "decline", "either")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL,
    kind            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    event_id        INTEGER UNIQUE,
    track_id        TEXT,
    track           TEXT NOT NULL,
    artist          TEXT NOT NULL,
    profile         TEXT,
    eval_state      TEXT,
    reason          TEXT NOT NULL DEFAULT '',
    detail          TEXT NOT NULL DEFAULT '',
    analysis_json   TEXT,
    rubric_version  TEXT NOT NULL DEFAULT '',
    model_id        TEXT NOT NULL DEFAULT '',
    note            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS feedback_status ON feedback(status, created_at);

CREATE TABLE IF NOT EXISTS golden_set (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    match_key                TEXT NOT NULL UNIQUE,
    track_id                 TEXT,
    track                    TEXT NOT NULL,
    artist                   TEXT NOT NULL,
    expected_family_friendly TEXT NOT NULL,
    expected_mixed_company   TEXT NOT NULL,
    expected_close_friends   TEXT NOT NULL,
    notes                    TEXT NOT NULL DEFAULT '',
    source                   TEXT NOT NULL,
    feedback_id              INTEGER,
    analysis_json            TEXT,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def match_key(track: str, artist: str) -> str:
    """Normalized identity for a golden-set song (case/whitespace-insensitive)."""
    return f"{' '.join(track.lower().split())}\x1f{' '.join(artist.lower().split())}"


def analysis_from_dict(data: dict | None) -> SongAnalysis | None:
    """Rebuild a SongAnalysis from its dataclasses.asdict() form (as carried on
    daemon events). Returns None for missing/malformed input."""
    if not data:
        return None
    try:
        cats = {name: CategoryRating(**data[name]) for name in CATEGORY_NAMES}
        return SongAnalysis(
            **cats,
            framing=data.get("framing", "neutral"),
            confidence=data.get("confidence", "unknown"),
            summary=data.get("summary", ""),
            model_id=data.get("model_id", ""),
            rubric_version=data.get("rubric_version", ""),
            evaluated_at=data.get("evaluated_at", 0.0),
        )
    except (KeyError, TypeError):
        return None


def derived_verdicts(analysis_json: str | None) -> dict[str, str] | None:
    """What the CURRENT profile code decides for a stored analysis, per profile."""
    analysis = analysis_from_dict(json.loads(analysis_json) if analysis_json else None)
    if analysis is None:
        return None
    return {p: derive_verdict(analysis, p) for p in PROFILES}


class FeedbackStore:
    def __init__(self, db_path: str = FEEDBACK_DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    # ------------------------------------------------------------------ feedback

    def add_feedback(
        self,
        *,
        kind: str,
        track: str,
        artist: str,
        track_id: str | None = None,
        event_id: int | None = None,
        profile: str | None = None,
        eval_state: str | None = None,
        reason: str = "",
        detail: str = "",
        analysis: dict | None = None,
        note: str = "",
    ) -> tuple[dict, bool]:
        """Insert a feedback row. Returns (row, created). A repeat for the same
        event_id is idempotent — returns the existing row with created=False."""
        if kind not in FEEDBACK_KINDS:
            raise ValueError(f"unknown feedback kind: {kind!r}")
        with self._connect() as db:
            if event_id is not None:
                existing = db.execute(
                    "SELECT * FROM feedback WHERE event_id = ?", (event_id,)
                ).fetchone()
                if existing:
                    return self._feedback_dict(existing), False
            cur = db.execute(
                """INSERT INTO feedback (created_at, kind, event_id, track_id, track,
                       artist, profile, eval_state, reason, detail, analysis_json,
                       rubric_version, model_id, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now(), kind, event_id, track_id, track, artist, profile,
                    eval_state, reason or "", detail or "",
                    json.dumps(analysis) if analysis else None,
                    (analysis or {}).get("rubric_version", ""),
                    (analysis or {}).get("model_id", ""),
                    note or "",
                ),
            )
            row = db.execute("SELECT * FROM feedback WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._feedback_dict(row), True

    def get_feedback(self, feedback_id: int) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
        return self._feedback_dict(row) if row else None

    def list_feedback(self, status: str | None = "pending", limit: int = 200) -> list[dict]:
        with self._connect() as db:
            if status:
                rows = db.execute(
                    "SELECT * FROM feedback WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._feedback_dict(r) for r in rows]

    def flagged_event_ids(self) -> set[int]:
        """Event ids that already have a 👎 (so the feed can render them as sent)."""
        with self._connect() as db:
            rows = db.execute("SELECT event_id FROM feedback WHERE event_id IS NOT NULL").fetchall()
        return {r[0] for r in rows}

    def set_status(self, feedback_id: int, status: str) -> bool:
        if status not in FEEDBACK_STATUSES:
            raise ValueError(f"unknown status: {status!r}")
        with self._connect() as db:
            cur = db.execute(
                "UPDATE feedback SET status = ? WHERE id = ?", (status, feedback_id)
            )
            return cur.rowcount > 0

    @staticmethod
    def _feedback_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["analysis"] = json.loads(d.pop("analysis_json")) if d.get("analysis_json") else None
        d["verdicts"] = derived_verdicts(json.dumps(d["analysis"])) if d["analysis"] else None
        return d

    # ---------------------------------------------------------------- golden set

    def upsert_golden(
        self,
        *,
        track: str,
        artist: str,
        expected: dict[str, str],
        source: str,
        notes: str = "",
        track_id: str | None = None,
        feedback_id: int | None = None,
        analysis: dict | None = None,
    ) -> dict:
        """Insert or update a golden-set song (matched by normalized track+artist).
        `expected` maps every profile to 'pass' | 'decline' | 'either'."""
        for p in PROFILES:
            if expected.get(p) not in EXPECTED_VALUES:
                raise ValueError(f"expected[{p!r}] must be one of {EXPECTED_VALUES}")
        key = match_key(track, artist)
        now = _now()
        with self._connect() as db:
            db.execute(
                """INSERT INTO golden_set (match_key, track_id, track, artist,
                       expected_family_friendly, expected_mixed_company,
                       expected_close_friends, notes, source, feedback_id,
                       analysis_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(match_key) DO UPDATE SET
                       track_id = COALESCE(excluded.track_id, golden_set.track_id),
                       expected_family_friendly = excluded.expected_family_friendly,
                       expected_mixed_company = excluded.expected_mixed_company,
                       expected_close_friends = excluded.expected_close_friends,
                       notes = excluded.notes,
                       feedback_id = COALESCE(excluded.feedback_id, golden_set.feedback_id),
                       analysis_json = COALESCE(excluded.analysis_json, golden_set.analysis_json),
                       updated_at = excluded.updated_at""",
                (
                    key, track_id, track, artist,
                    expected["family_friendly"], expected["mixed_company"],
                    expected["close_friends"], notes or "", source, feedback_id,
                    json.dumps(analysis) if analysis else None, now, now,
                ),
            )
            row = db.execute("SELECT * FROM golden_set WHERE match_key = ?", (key,)).fetchone()
        return self._golden_dict(row)

    def promote(self, feedback_id: int, expected: dict[str, str], notes: str = "") -> dict | None:
        """Copy a feedback row into the golden set with the reviewer's expected
        verdicts, and mark the feedback promoted. None if the id doesn't exist."""
        fb = self.get_feedback(feedback_id)
        if fb is None:
            return None
        golden = self.upsert_golden(
            track=fb["track"],
            artist=fb["artist"],
            track_id=fb["track_id"],
            expected=expected,
            notes=notes,
            source="feedback",
            feedback_id=feedback_id,
            analysis=fb["analysis"],
        )
        self.set_status(feedback_id, "promoted")
        return golden

    def list_golden(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM golden_set ORDER BY artist COLLATE NOCASE, track COLLATE NOCASE"
            ).fetchall()
        return [self._golden_dict(r) for r in rows]

    def delete_golden(self, golden_id: int) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM golden_set WHERE id = ?", (golden_id,))
            return cur.rowcount > 0

    @staticmethod
    def _golden_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d.pop("match_key", None)
        d["analysis"] = json.loads(d.pop("analysis_json")) if d.get("analysis_json") else None
        d["expected"] = {p: d.pop(f"expected_{p}") for p in PROFILES}
        return d
