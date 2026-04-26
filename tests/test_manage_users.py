"""Integration tests for scripts/manage_users.py CLI subcommands.

Tests call cmd_generate_url() and cmd_remove() directly to avoid subprocess overhead
and enable tmp_path filesystem isolation. SpotifyOAuth is mocked to avoid real
network calls and credential requirements.
"""
import json
import os
import signal
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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


# ---------------------------------------------------------------------------
# Phase 30: _stop_daemon_via_pid tests (OPS-02, D-12) — TDD RED scaffolds
# These tests FAIL against unmodified codebase (_stop_daemon_via_pid not yet defined).
# ---------------------------------------------------------------------------

def test_remove_sends_sigterm_to_daemon(tmp_path):
    """_stop_daemon_via_pid sends SIGTERM to the pid from daemon.pid file (D-12).

    Fails with ImportError: _stop_daemon_via_pid not yet defined in manage_users.py.
    """
    from scripts.manage_users import _stop_daemon_via_pid  # ImportError until Phase 30

    uid = "testuid_sigterm"
    pid_dir = tmp_path / "users" / uid
    pid_dir.mkdir(parents=True)
    fake_pid = 99997
    (pid_dir / "daemon.pid").write_text(str(fake_pid))

    kill_calls = []

    def fake_kill(pid, sig):
        kill_calls.append((pid, sig))
        if sig == 0:
            # Process is dead after SIGTERM — raise ProcessLookupError on probe
            raise ProcessLookupError()

    with patch("os.kill", side_effect=fake_kill):
        _stop_daemon_via_pid(uid, str(tmp_path))

    assert (fake_pid, signal.SIGTERM) in kill_calls, (
        f"SIGTERM must be sent to pid {fake_pid}; got kill calls: {kill_calls}"
    )


def test_remove_sigkills_if_process_survives(tmp_path):
    """_stop_daemon_via_pid sends SIGKILL if process is still alive after SIGTERM (D-12).

    Fails with ImportError: _stop_daemon_via_pid not yet defined.
    """
    from scripts.manage_users import _stop_daemon_via_pid

    uid = "testuid_sigkill"
    pid_dir = tmp_path / "users" / uid
    pid_dir.mkdir(parents=True)
    fake_pid = 99996
    (pid_dir / "daemon.pid").write_text(str(fake_pid))

    kill_calls = []

    def fake_kill(pid, sig):
        kill_calls.append((pid, sig))
        # Process never dies — os.kill(pid, 0) always succeeds (no ProcessLookupError)
        # SIGTERM and SIGKILL don't raise; probe (sig==0) also doesn't raise
        # Simulating: process ignores SIGTERM and stays alive

    # We also need to mock time.sleep and time.monotonic to avoid real waiting
    start_time = [0.0]
    fake_monotonic_calls = [0]

    def fake_monotonic():
        # Advance time rapidly so the 5s deadline is reached quickly
        fake_monotonic_calls[0] += 1
        # After a few probe calls, jump past deadline
        if fake_monotonic_calls[0] > 5:
            return 10.0  # past 5s deadline
        return float(fake_monotonic_calls[0]) * 0.5

    with patch("os.kill", side_effect=fake_kill), \
         patch("time.sleep"), \
         patch("time.monotonic", side_effect=fake_monotonic):
        _stop_daemon_via_pid(uid, str(tmp_path))

    sigkill_calls = [(p, s) for p, s in kill_calls if s == signal.SIGKILL]
    assert len(sigkill_calls) >= 1, (
        f"SIGKILL must be sent after timeout; got kill calls: {kill_calls}"
    )
    assert sigkill_calls[0][0] == fake_pid


def test_remove_handles_missing_pid_file(tmp_path):
    """_stop_daemon_via_pid succeeds gracefully when daemon.pid does not exist (D-12).

    Fails with ImportError: _stop_daemon_via_pid not yet defined.
    """
    from scripts.manage_users import _stop_daemon_via_pid

    uid = "testuid_nopid"
    pid_dir = tmp_path / "users" / uid
    pid_dir.mkdir(parents=True)
    # NO daemon.pid file created

    # Should not raise any exception
    try:
        _stop_daemon_via_pid(uid, str(tmp_path))
    except FileNotFoundError:
        pytest.fail("_stop_daemon_via_pid must handle missing PID file gracefully (no FileNotFoundError)")


def test_remove_handles_already_dead_process(tmp_path):
    """_stop_daemon_via_pid succeeds when process is already dead (SIGTERM raises ProcessLookupError).

    Fails with ImportError: _stop_daemon_via_pid not yet defined.
    """
    from scripts.manage_users import _stop_daemon_via_pid

    uid = "testuid_dead"
    pid_dir = tmp_path / "users" / uid
    pid_dir.mkdir(parents=True)
    fake_pid = 99995
    (pid_dir / "daemon.pid").write_text(str(fake_pid))

    def fake_kill(pid, sig):
        # Process is already dead — SIGTERM raises ProcessLookupError immediately
        raise ProcessLookupError()

    # Should not raise any exception
    try:
        with patch("os.kill", side_effect=fake_kill):
            _stop_daemon_via_pid(uid, str(tmp_path))
    except ProcessLookupError:
        pytest.fail(
            "_stop_daemon_via_pid must handle already-dead process gracefully (no ProcessLookupError)"
        )
