"""Integration tests for scripts/manage_users.py CLI subcommands.

Tests call cmd_generate_url() and cmd_remove() directly to avoid subprocess overhead
and enable tmp_path filesystem isolation. SpotifyOAuth is mocked to avoid real
network calls and credential requirements.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The script inserts project root into sys.path on import — safe to do here.
from scripts.manage_users import cmd_generate_url, cmd_remove
from user_registry import MAX_USERS, UserRegistry

FAKE_OAUTH_URL = "https://accounts.spotify.com/authorize?client_id=test&state={uid}"


def fake_oauth_url(uid: str) -> str:
    return FAKE_OAUTH_URL.format(uid=uid)


@pytest.fixture()
def spotify_env(monkeypatch):
    """Inject required Spotify env vars so URL generation doesn't bail early."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "https://localhost/callback")


@pytest.fixture()
def patched_registry(tmp_path, monkeypatch):
    """Patch UserRegistry in manage_users module to use tmp_path as base_dir."""
    original_init = UserRegistry.__init__

    def _init_with_tmp(self, base_dir="."):
        original_init(self, base_dir=str(tmp_path))

    monkeypatch.setattr("scripts.manage_users.UserRegistry", UserRegistry)
    monkeypatch.setattr(UserRegistry, "__init__", _init_with_tmp)
    return tmp_path


@pytest.fixture()
def mock_spotify_oauth():
    """Mock SpotifyOAuth so no real OAuth calls are made."""
    with patch("scripts.manage_users.SpotifyOAuth") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?client_id=x&state=FAKE_UID"
        )
        mock_cls.return_value = mock_instance
        yield mock_cls


# ---------------------------------------------------------------------------
# generate-url tests
# ---------------------------------------------------------------------------

def test_generate_url_missing_env_returns_1(monkeypatch):
    """Missing SPOTIFY_CLIENT_ID causes exit code 1."""
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    result = cmd_generate_url("alice")
    assert result == 1


def test_generate_url_creates_user_dir(
    spotify_env, patched_registry, mock_spotify_oauth, capsys
):
    result = cmd_generate_url("alice")
    assert result == 0
    users_root = patched_registry / "users"
    user_dirs = list(users_root.iterdir())
    assert len(user_dirs) == 1
    uid_dir = user_dirs[0]
    assert (uid_dir / "state.json").exists()
    assert (uid_dir / "data" / "events.jsonl").exists()
    assert (uid_dir / "token_cache").is_dir()


def test_generate_url_writes_registry(
    spotify_env, patched_registry, mock_spotify_oauth, capsys
):
    cmd_generate_url("alice")
    registry_file = patched_registry / "users.json"
    assert registry_file.exists()
    data = json.loads(registry_file.read_text())
    assert len(data["users"]) == 1


def test_generate_url_status_pending(
    spotify_env, patched_registry, mock_spotify_oauth, capsys
):
    cmd_generate_url("alice")
    data = json.loads((patched_registry / "users.json").read_text())
    assert data["users"][0]["status"] == "pending"


def test_generate_url_output_contains_uid(
    spotify_env, patched_registry, mock_spotify_oauth, capsys
):
    cmd_generate_url("alice")
    captured = capsys.readouterr()
    # The uid from users.json should appear in stdout
    data = json.loads((patched_registry / "users.json").read_text())
    uid = data["users"][0]["uid"]
    assert uid in captured.out


def test_generate_url_output_contains_state_param(
    spotify_env, patched_registry, mock_spotify_oauth, capsys
):
    cmd_generate_url("alice")
    captured = capsys.readouterr()
    assert "state=" in captured.out


def test_generate_url_limit_returns_1(
    spotify_env, patched_registry, mock_spotify_oauth
):
    """6th provision attempt returns exit code 1."""
    reg = UserRegistry(base_dir=str(patched_registry))
    for i in range(MAX_USERS):
        reg.provision(f"user{i}")
    result = cmd_generate_url("overflow")
    assert result == 1


# ---------------------------------------------------------------------------
# remove tests
# ---------------------------------------------------------------------------

def test_remove_valid_uid_returns_0(patched_registry):
    reg = UserRegistry(base_dir=str(patched_registry))
    record = reg.provision("alice")
    result = cmd_remove(record["uid"])
    assert result == 0


def test_remove_deletes_directory(patched_registry):
    reg = UserRegistry(base_dir=str(patched_registry))
    record = reg.provision("alice")
    uid = record["uid"]
    cmd_remove(uid)
    assert not (patched_registry / "users" / uid).exists()


def test_remove_unknown_uid_returns_1(patched_registry):
    result = cmd_remove("nonexistent_uid_string")
    assert result == 1


# ---------------------------------------------------------------------------
# list tests
# ---------------------------------------------------------------------------

from scripts.manage_users import cmd_list  # noqa: E402


def test_list_empty_registry_prints_message(patched_registry, capsys):
    """cmd_list() with empty registry prints 'No users registered.' and returns 0."""
    result = cmd_list()
    captured = capsys.readouterr()
    assert result == 0
    assert "No users registered." in captured.out


def test_list_pending_user_shows_truncated_uid_name_and_status(patched_registry, capsys):
    """cmd_list() with one pending user shows truncated uid, name, and 'pending'."""
    reg = UserRegistry(base_dir=str(patched_registry))
    record = reg.provision("alice")
    uid = record["uid"]
    result = cmd_list()
    captured = capsys.readouterr()
    assert result == 0
    assert uid[:8] + "..." in captured.out
    assert "alice" in captured.out
    assert "pending" in captured.out


def test_list_active_user_shows_active_status(patched_registry, capsys):
    """cmd_list() with one active user shows 'active' in status column."""
    reg = UserRegistry(base_dir=str(patched_registry))
    record = reg.provision("bob")
    reg.activate(record["uid"])
    result = cmd_list()
    captured = capsys.readouterr()
    assert result == 0
    assert "active" in captured.out


def test_list_max_users_shows_all_rows(patched_registry, capsys):
    """cmd_list() with MAX_USERS users prints all 5 rows."""
    reg = UserRegistry(base_dir=str(patched_registry))
    names = [f"user{i}" for i in range(MAX_USERS)]
    for name in names:
        reg.provision(name)
    result = cmd_list()
    captured = capsys.readouterr()
    assert result == 0
    for name in names:
        assert name in captured.out


def test_list_does_not_expose_full_uid(patched_registry, capsys):
    """cmd_list() output does not expose the full uid."""
    reg = UserRegistry(base_dir=str(patched_registry))
    record = reg.provision("carol")
    uid = record["uid"]
    cmd_list()
    captured = capsys.readouterr()
    # Full uid must not appear; only the truncated prefix (first 8 chars + "...") is shown
    assert uid not in captured.out
    assert uid[:8] + "..." in captured.out
