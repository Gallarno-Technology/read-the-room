"""Tests for UserRegistry — per-user data directory management."""
import json
import re
from pathlib import Path

import pytest

from user_registry import UserRegistry, MAX_USERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_registry(tmp_path: Path) -> UserRegistry:
    return UserRegistry(base_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# provision() tests
# ---------------------------------------------------------------------------

def test_provision_creates_directory(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    assert (tmp_path / "users" / record["uid"]).is_dir()


def test_provision_creates_state_json(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    state_path = tmp_path / "users" / record["uid"] / "state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data["last_track_id"] is None
    assert data["family_safe_mode"] is False
    assert data["active_profile"] == "kids_present"


def test_provision_creates_data_files(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    base = tmp_path / "users" / record["uid"] / "data"
    assert (base / "events.jsonl").exists()
    assert (base / "now_playing.json").exists()


def test_provision_creates_token_cache_dir(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    token_dir = tmp_path / "users" / record["uid"] / "token_cache"
    assert token_dir.is_dir()


def test_provision_writes_users_json(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    registry_path = tmp_path / "users.json"
    assert registry_path.exists()
    data = json.loads(registry_path.read_text())
    assert len(data["users"]) == 1
    entry = data["users"][0]
    assert entry["uid"] == record["uid"]
    assert entry["name"] == "alice"
    assert entry["status"] == "pending"
    assert "created_at" in entry


def test_provision_uid_format(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    uid = record["uid"]
    assert len(uid) == 22
    # URL-safe base64 uses only A-Z a-z 0-9 - _
    assert re.fullmatch(r"[A-Za-z0-9_-]{22}", uid), f"uid not URL-safe: {uid!r}"


def test_provision_atomicity(tmp_path):
    reg = make_registry(tmp_path)
    reg.provision("alice")
    assert not (tmp_path / "users.json.tmp").exists()


def test_provision_limit(tmp_path):
    reg = make_registry(tmp_path)
    for i in range(MAX_USERS):
        reg.provision(f"user{i}")
    with pytest.raises(RuntimeError, match="User limit reached"):
        reg.provision("overflow")


def test_provision_duplicate_name_allowed(tmp_path):
    """Duplicate names are allowed — uid is the unique key."""
    reg = make_registry(tmp_path)
    r1 = reg.provision("alice")
    r2 = reg.provision("alice")
    assert r1["uid"] != r2["uid"]
    assert len(reg.load()) == 2


# ---------------------------------------------------------------------------
# remove() tests
# ---------------------------------------------------------------------------

def test_remove_deletes_directory(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    uid = record["uid"]
    reg.remove(uid)
    assert not (tmp_path / "users" / uid).exists()


def test_remove_updates_registry(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    reg.remove(record["uid"])
    users = reg.load()
    assert all(u["uid"] != record["uid"] for u in users)


def test_remove_unknown_uid_raises(tmp_path):
    reg = make_registry(tmp_path)
    with pytest.raises(ValueError, match="Unknown uid"):
        reg.remove("nonexistent_uid_string")


# ---------------------------------------------------------------------------
# load() tests
# ---------------------------------------------------------------------------

def test_load_empty_when_no_file(tmp_path):
    reg = make_registry(tmp_path)
    assert reg.load() == []


# ---------------------------------------------------------------------------
# user_paths() tests
# ---------------------------------------------------------------------------

def test_user_paths_returns_correct_keys(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    paths = reg.user_paths(record["uid"])
    assert set(paths.keys()) == {"state_path", "events_path", "now_playing_path", "cache_path", "user_dir"}


def test_user_paths_values_are_correct(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    uid = record["uid"]
    paths = reg.user_paths(uid)
    expected_base = str(tmp_path / "users" / uid)
    assert paths["state_path"] == f"{expected_base}/state.json"
    assert paths["events_path"] == f"{expected_base}/data/events.jsonl"
    assert paths["now_playing_path"] == f"{expected_base}/data/now_playing.json"
    assert paths["cache_path"] == f"{expected_base}/token_cache/.cache"
    assert paths["user_dir"] == expected_base


def test_user_paths_unknown_raises(tmp_path):
    reg = make_registry(tmp_path)
    with pytest.raises(ValueError, match="Unknown uid"):
        reg.user_paths("bad_uid")


# ---------------------------------------------------------------------------
# ISOL-03: lyrics_cache.db is NOT created in any per-user directory
# ---------------------------------------------------------------------------

def test_lyrics_cache_not_in_user_dir(tmp_path):
    reg = make_registry(tmp_path)
    record = reg.provision("alice")
    user_dir = tmp_path / "users" / record["uid"]
    db_files = list(user_dir.rglob("lyrics_cache.db"))
    assert db_files == [], f"lyrics_cache.db should not be inside user dir, found: {db_files}"
