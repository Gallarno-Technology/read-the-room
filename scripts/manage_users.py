#!/usr/bin/env python3
"""Operator CLI for managing per-user data directories and registry.

Usage:
    python scripts/manage_users.py generate-url <name>
        Provisions a new user and prints their uid and Spotify OAuth URL.
        The url contains the uid in the `state` parameter.
        User must complete Spotify authorization before the uid is active.

    python scripts/manage_users.py remove <uid>
        Removes the user's data directory and registry entry.
        Sends SIGTERM to the running daemon (if any) before deleting data.

    python scripts/manage_users.py list
        Prints all registered users with their truncated uid, name, and status.

Invoked from the project root so relative paths (users/, users.json) resolve correctly.
"""
import os
import signal
import sys
import time

# Allow `python scripts/manage_users.py` from project root to find user_registry
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

from user_registry import MAX_USERS, UserRegistry

load_dotenv()

REQUIRED_ENV_VARS_FOR_URL = [
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URI",
]

SCOPE = "user-read-currently-playing user-modify-playback-state"


def cmd_generate_url(name: str) -> int:
    """Provision a new user and print their uid + Spotify OAuth URL.

    Returns exit code (0 = success, 1 = error).
    """
    missing = [v for v in REQUIRED_ENV_VARS_FOR_URL if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your Spotify credentials.")
        return 1

    registry = UserRegistry(base_dir=".")
    try:
        record = registry.provision(name)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    uid = record["uid"]

    # Build OAuth URL with uid baked into the state parameter (D-10)
    # CacheFileHandler is required by SpotifyOAuth but token exchange happens
    # in Phase 29 — we use a placeholder path here that will be overwritten later.
    cache_path = f"users/{uid}/token_cache/.cache"
    cache_handler = CacheFileHandler(cache_path=cache_path)
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=SCOPE,
        open_browser=False,
        cache_handler=cache_handler,
        state=uid,
    )
    oauth_url = auth_manager.get_authorize_url()

    print()
    print("User created.")
    print()
    print(f"  UID:  {uid}")
    print(f"  Name: {record['name']}")
    print()
    print("Authorize this user by opening the URL below in a browser.")
    print("The UID is only active after the user completes Spotify authorization.")
    print()
    print(f"  {oauth_url}")
    print()
    return 0


def _stop_daemon_via_pid(uid: str, base_dir: str) -> None:
    """Send SIGTERM to uid's daemon via PID file. Wait 5s, then SIGKILL.

    Per D-12: called by cmd_remove before deleting user directory.
    Handles FileNotFoundError (no PID file) and ProcessLookupError (dead process) gracefully.
    """
    pid_path = os.path.join(base_dir, "users", uid, "daemon.pid")
    try:
        pid = int(open(pid_path).read().strip())
    except FileNotFoundError:
        return  # no PID file — daemon not running or already stopped
    except (ValueError, OSError) as exc:
        print(f"WARNING: could not read daemon.pid for uid={uid}: {exc}")
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return  # process already dead
    # Wait up to 5 seconds for clean shutdown
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)  # probe — raises ProcessLookupError if dead
        except ProcessLookupError:
            return  # clean exit within timeout
        time.sleep(0.1)
    # Still alive after 5s — SIGKILL
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # race: died between probe and kill


def cmd_remove(uid: str) -> int:
    """Remove a user's data directory and registry entry.

    Sends SIGTERM to the running daemon (if any) via PID file before
    deleting data — completing OPS-02 daemon-stop debt from Phase 27 (D-12).
    Returns exit code (0 = success, 1 = error).
    """
    _stop_daemon_via_pid(uid, ".")
    registry = UserRegistry(base_dir=".")
    try:
        registry.remove(uid)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"User {uid} removed.")
    return 0


def cmd_list() -> int:
    """Print all registered users with truncated uid, name, and status.

    Returns exit code (0 = success).
    """
    registry = UserRegistry(base_dir=".")
    users = registry.load()
    if not users:
        print("No users registered.")
        return 0
    print(f"{'UID':12}  {'NAME':20}  STATUS")
    print("-" * 42)
    for u in users:
        short_uid = u["uid"][:8] + "..."
        print(f"{short_uid:12}  {u['name']:20}  {u['status']}")
    return 0


def usage() -> None:
    print("Usage:")
    print("  python scripts/manage_users.py generate-url <name>")
    print("  python scripts/manage_users.py remove <uid>")
    print("  python scripts/manage_users.py list")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        usage()
        sys.exit(1)

    subcommand = args[0]

    if subcommand == "generate-url":
        if len(args) != 2:
            print("ERROR: generate-url requires exactly one argument: <name>")
            usage()
            sys.exit(1)
        sys.exit(cmd_generate_url(args[1]))

    elif subcommand == "remove":
        if len(args) != 2:
            print("ERROR: remove requires exactly one argument: <uid>")
            usage()
            sys.exit(1)
        sys.exit(cmd_remove(args[1]))

    elif subcommand == "list":
        sys.exit(cmd_list())

    else:
        print(f"ERROR: Unknown subcommand: {subcommand!r}")
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
