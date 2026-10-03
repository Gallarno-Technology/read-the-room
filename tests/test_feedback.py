"""Tests for listener feedback + golden set (feedback_store, web_ui endpoints,
and the daemon/content_checker fields that feed them)."""

import dataclasses
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_ui"),
)

import main as web_ui_main
from fastapi.testclient import TestClient

from content_checker import ContentChecker
from feedback_store import FeedbackStore, analysis_from_dict
from sentiment_service import CategoryRating, SongAnalysis


def _analysis(**overrides) -> SongAnalysis:
    base = dict(
        sexual=CategoryRating("none"),
        drug_references=CategoryRating("none"),
        violence=CategoryRating("none"),
        dark_themes=CategoryRating("present", "Graveyard, monsters, vampires"),
        language=CategoryRating("none"),
        framing="neutral",
        confidence="known",
        summary="Playful Halloween novelty.",
        model_id="claude-haiku-4-5-20251001",
        rubric_version="v2",
        evaluated_at=1.0,
    )
    base.update(overrides)
    return SongAnalysis(**base)


MONSTER_MASH = dataclasses.asdict(_analysis())


# ---------------------------------------------------------------------------
# feedback_store
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(str(tmp_path / "feedback.db"))


def test_analysis_round_trips_through_dict():
    assert analysis_from_dict(MONSTER_MASH) == _analysis()
    assert analysis_from_dict(None) is None
    assert analysis_from_dict({"framing": "neutral"}) is None


def test_add_feedback_snapshots_analysis_and_derives_verdicts(store):
    row, created = store.add_feedback(
        kind="wrong_skip", event_id=7, track_id="t1", track="Monster Mash",
        artist="Bobby Pickett", profile="family_friendly", analysis=MONSTER_MASH,
    )
    assert created
    assert row["status"] == "pending"
    assert row["rubric_version"] == "v2"
    assert row["model_id"] == "claude-haiku-4-5-20251001"
    assert row["analysis"]["dark_themes"]["severity"] == "present"
    # dark_themes=present → FF declines, MC/CF pass under current rules
    assert row["verdicts"] == {
        "family_friendly": "decline", "mixed_company": "pass", "close_friends": "pass",
    }


def test_feedback_is_idempotent_per_event(store):
    first, created1 = store.add_feedback(kind="wrong_skip", event_id=7, track="A", artist="B")
    second, created2 = store.add_feedback(kind="wrong_skip", event_id=7, track="A", artist="B")
    assert created1 and not created2
    assert first["id"] == second["id"]
    assert store.flagged_event_ids() == {7}


def test_add_feedback_rejects_unknown_kind(store):
    with pytest.raises(ValueError):
        store.add_feedback(kind="thumbs_up", track="A", artist="B")


def test_promote_upserts_golden_and_marks_promoted(store):
    row, _ = store.add_feedback(
        kind="wrong_skip", event_id=1, track_id="t1", track="Monster Mash",
        artist="Bobby Pickett", profile="family_friendly", analysis=MONSTER_MASH,
    )
    expected = {"family_friendly": "pass", "mixed_company": "pass", "close_friends": "pass"}
    golden = store.promote(row["id"], expected, notes="kids' novelty song")
    assert golden["expected"] == expected
    assert golden["source"] == "feedback"
    assert golden["track_id"] == "t1"
    assert golden["analysis"]["dark_themes"]["severity"] == "present"
    assert store.get_feedback(row["id"])["status"] == "promoted"
    assert store.list_feedback("pending") == []


def test_golden_matches_case_insensitively_and_keeps_track_id(store):
    exp = {"family_friendly": "decline", "mixed_company": "pass", "close_friends": "pass"}
    store.upsert_golden(track="House Tour", artist="Sabrina Carpenter", expected=exp, source="fixture")
    exp2 = dict(exp, mixed_company="either")
    updated = store.upsert_golden(
        track="house  tour", artist="SABRINA CARPENTER", expected=exp2,
        source="feedback", track_id="t9",
    )
    rows = store.list_golden()
    assert len(rows) == 1
    assert updated["expected"]["mixed_company"] == "either"
    assert updated["track_id"] == "t9"
    assert updated["source"] == "fixture"  # original provenance kept


def test_golden_rejects_bad_expected(store):
    with pytest.raises(ValueError):
        store.upsert_golden(
            track="A", artist="B", source="fixture",
            expected={"family_friendly": "maybe", "mixed_company": "pass", "close_friends": "pass"},
        )


# ---------------------------------------------------------------------------
# content_checker — analysis carried on the result
# ---------------------------------------------------------------------------


def test_result_from_analysis_carries_full_analysis():
    checker = ContentChecker(active_profile="family_friendly")
    result = checker._result_from_analysis(_analysis())
    assert result.action == "skip"
    assert result.analysis == MONSTER_MASH


# ---------------------------------------------------------------------------
# daemon — skip events carry track_id / profile / analysis
# ---------------------------------------------------------------------------


def test_skip_event_carries_feedback_fields():
    import daemon
    from content_checker import TrackEvalResult

    result = TrackEvalResult(
        action="skip", reason="sentiment", severity=3, dark_themes=True,
        detail="Playful Halloween novelty.", analysis=MONSTER_MASH,
    )
    track = {"name": "Monster Mash", "artists": [{"name": "Bobby Pickett"}]}
    evt = daemon._skip_event("skip", "t1", track, result, "family_friendly")
    assert evt["type"] == "skip"
    assert evt["track_id"] == "t1"
    assert evt["profile"] == "family_friendly"
    assert evt["analysis"] == MONSTER_MASH
    assert evt["dark_themes"] is True


# ---------------------------------------------------------------------------
# web_ui endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def paths(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"family_safe_mode": True, "active_profile": "family_friendly"}))
    events = data / "events.jsonl"
    events.write_text("")
    now_playing = data / "now_playing.json"
    monkeypatch.delenv("FEEDBACK_DB_PATH", raising=False)
    monkeypatch.setattr(web_ui_main, "STATE_PATH", str(state))
    monkeypatch.setattr(web_ui_main, "EVENTS_PATH", str(events))
    monkeypatch.setattr(web_ui_main, "NOW_PLAYING_PATH", str(now_playing))
    return {"events": events, "now_playing": now_playing, "db": data / "feedback.db"}


@pytest.fixture
def client(paths):
    mock_sp = MagicMock()
    with patch.object(web_ui_main, "_sp_init", return_value=mock_sp):
        with TestClient(web_ui_main.app, raise_server_exceptions=False) as c:
            c._mock_sp = mock_sp
            yield c


def _write_events(path, events):
    path.write_text("".join(json.dumps(e) + "\n" for e in events))


SKIP_EVENT = {
    "id": 42, "type": "skip", "track_id": "t1", "track": "Monster Mash",
    "artist": "Bobby Pickett", "reason": "sentiment", "dark_themes": True,
    "detail": "Playful Halloween novelty.", "profile": "family_friendly",
    "analysis": MONSTER_MASH, "timestamp": "2026-10-03T21:24:08+00:00",
}


def test_post_feedback_snapshots_event_server_side(client, paths):
    _write_events(paths["events"], [{"id": 41, "type": "track_change"}, SKIP_EVENT])
    resp = client.post("/feedback", json={"event_id": 42, "note": "kids song"})
    assert resp.status_code == 201
    fb = resp.json()["feedback"]
    assert fb["kind"] == "wrong_skip"
    assert fb["profile"] == "family_friendly"
    assert fb["eval_state"] == "skipped"
    assert fb["note"] == "kids song"
    assert fb["analysis"] == MONSTER_MASH
    assert paths["db"].exists()

    again = client.post("/feedback", json={"event_id": 42})
    assert again.status_code == 200
    assert again.json()["created"] is False


def test_post_feedback_on_five_skip_warning_records_paused(client, paths):
    _write_events(paths["events"], [dict(SKIP_EVENT, type="five_skip_warning")])
    resp = client.post("/feedback", json={"event_id": 42})
    assert resp.status_code == 201
    assert resp.json()["feedback"]["eval_state"] == "paused"


def test_post_feedback_unknown_or_non_skip_event_404(client, paths):
    _write_events(paths["events"], [{"id": 1, "type": "track_change", "track": "X"}])
    assert client.post("/feedback", json={"event_id": 1}).status_code == 404
    assert client.post("/feedback", json={"event_id": 999}).status_code == 404
    # legacy warning without track details can't be flagged
    _write_events(paths["events"], [{"id": 2, "type": "five_skip_warning"}])
    assert client.post("/feedback", json={"event_id": 2}).status_code == 404


def test_feed_marks_flagged_events(client, paths):
    _write_events(paths["events"], [dict(SKIP_EVENT, id=1), dict(SKIP_EVENT, id=2)])
    client.post("/feedback", json={"event_id": 2})
    feed = {e["id"]: e for e in client.get("/feed").json()}
    assert feed[2]["feedback_sent"] is True
    assert feed[1]["feedback_sent"] is False


def test_manual_skip_logs_feedback_with_now_playing_snapshot(client, paths):
    paths["now_playing"].write_text(json.dumps({
        "track_id": "t5", "track": "Super Freak", "artist": "Rick James",
        "eval_state": "passed", "profile": "mixed_company", "detail": "Innuendo.",
        "analysis": MONSTER_MASH,
    }))
    assert client.post("/skip").status_code == 200
    rows = client.get("/api/feedback").json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "manual_skip"
    assert rows[0]["track"] == "Super Freak"
    assert rows[0]["profile"] == "mixed_company"
    assert rows[0]["eval_state"] == "passed"


def test_manual_skip_without_now_playing_still_skips(client, paths):
    assert client.post("/skip").status_code == 200
    assert client.get("/api/feedback").json() == []


def test_failed_skip_does_not_log_feedback(client, paths):
    import spotipy

    paths["now_playing"].write_text(json.dumps({"track_id": "t5", "track": "X", "artist": "Y"}))
    client._mock_sp.next_track.side_effect = spotipy.SpotifyException(
        http_status=429, code=-1, msg="rate limited"
    )
    assert client.post("/skip").status_code == 503
    assert client.get("/api/feedback").json() == []


def test_promote_dismiss_and_golden_set_flow(client, paths):
    _write_events(paths["events"], [SKIP_EVENT, dict(SKIP_EVENT, id=43, track="Thriller")])
    fb1 = client.post("/feedback", json={"event_id": 42}).json()["feedback"]
    fb2 = client.post("/feedback", json={"event_id": 43}).json()["feedback"]

    expected = {"family_friendly": "pass", "mixed_company": "pass", "close_friends": "pass"}
    resp = client.post(f"/api/feedback/{fb1['id']}/promote", json=dict(expected, notes="novelty"))
    assert resp.status_code == 200
    assert resp.json()["expected"] == expected

    assert client.post(f"/api/feedback/{fb2['id']}/dismiss").status_code == 200
    assert client.get("/api/feedback").json() == []
    statuses = {f["track"]: f["status"] for f in client.get("/api/feedback?status=all").json()}
    assert statuses == {"Monster Mash": "promoted", "Thriller": "dismissed"}

    golden = client.get("/api/golden-set").json()
    assert [g["track"] for g in golden] == ["Monster Mash"]

    csv_resp = client.get("/golden-set.csv")
    assert csv_resp.status_code == 200
    assert "Monster Mash,Bobby Pickett,t1,pass,pass,pass,novelty,feedback" in csv_resp.text

    assert client.delete(f"/api/golden-set/{golden[0]['id']}").status_code == 200
    assert client.get("/api/golden-set").json() == []


def test_promote_validation(client, paths):
    bad = {"family_friendly": "maybe", "mixed_company": "pass", "close_friends": "pass"}
    assert client.post("/api/feedback/999/promote", json=dict(bad, family_friendly="pass")).status_code == 404
    _write_events(paths["events"], [SKIP_EVENT])
    fb = client.post("/feedback", json={"event_id": 42}).json()["feedback"]
    assert client.post(f"/api/feedback/{fb['id']}/promote", json=bad).status_code == 400
    assert client.get("/api/feedback?status=bogus").status_code == 400


def test_review_page_serves(client):
    resp = client.get("/review")
    assert resp.status_code == 200
    assert "Golden set" in resp.text
