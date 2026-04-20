"""User registry — per-user data directory management.

Owns all on-disk operations for users/{uid}/ layout and users.json persistence.
Called by scripts/manage_users.py (Phase 27) and web_ui OAuth callback (Phase 29).
"""
import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

MAX_USERS = 5

_INITIAL_STATE = {
    "last_track_id": None,
    "family_safe_mode": False,
    "active_profile": "kids_present",
}


class UserRegistry:
    def __init__(self, base_dir: str = ".") -> None:
        self.base_dir = Path(base_dir)
        self._registry_path = self.base_dir / "users.json"
        self._users_root = self.base_dir / "users"

    # --- public API ---

    def provision(self, name: str) -> dict:
        """Create a new user entry and scaffold their data directory.

        Returns the new user record dict.
        Raises RuntimeError if the 5-user limit is reached.
        """
        users = self.load()
        if len(users) >= MAX_USERS:
            raise RuntimeError(f"User limit reached (max {MAX_USERS})")

        uid = secrets.token_urlsafe(16)
        created_at = datetime.now(timezone.utc).isoformat()
        record = {"uid": uid, "name": name, "created_at": created_at, "status": "pending"}

        self._scaffold_user_dir(uid)
        users.append(record)
        self._save(users)
        return record

    def remove(self, uid: str) -> None:
        """Delete user data directory and remove their registry entry.

        Raises ValueError if uid not found.
        """
        users = self.load()
        remaining = [u for u in users if u["uid"] != uid]
        if len(remaining) == len(users):
            raise ValueError(f"Unknown uid: {uid!r}")

        user_dir = self._users_root / uid
        if user_dir.exists():
            shutil.rmtree(user_dir)

        self._save(remaining)

    def activate(self, uid: str) -> None:
        """Flip user status from 'pending' to 'active'. Atomic write via _save().

        Raises ValueError if uid not found in registry.
        Called by web_ui OAuth callback after successful token exchange (Phase 29, AUTH-01).
        """
        users = self.load()
        for user in users:
            if user["uid"] == uid:
                user["status"] = "active"
                break
        else:
            raise ValueError(f"Unknown uid: {uid!r}")
        self._save(users)

    def load(self) -> list[dict]:
        """Return list of all user dicts. Returns [] if users.json is missing."""
        if not self._registry_path.exists():
            return []
        with open(self._registry_path) as f:
            data = json.load(f)
        return data.get("users", [])

    def user_paths(self, uid: str) -> dict:
        """Return per-user env-var-ready path strings.

        Keys: state_path, events_path, now_playing_path, cache_path, user_dir
        Raises ValueError if uid not in registry.
        """
        users = self.load()
        if not any(u["uid"] == uid for u in users):
            raise ValueError(f"Unknown uid: {uid!r}")
        base = self._users_root / uid
        return {
            "state_path": str(base / "state.json"),
            "events_path": str(base / "data" / "events.jsonl"),
            "now_playing_path": str(base / "data" / "now_playing.json"),
            "cache_path": str(base / "token_cache" / ".cache"),
            "user_dir": str(base),
        }

    # --- private helpers ---

    def _scaffold_user_dir(self, uid: str) -> None:
        base = self._users_root / uid
        data_dir = base / "data"
        token_dir = base / "token_cache"

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(token_dir, exist_ok=True)

        # state.json — initial daemon state
        state_path = base / "state.json"
        with open(state_path, "w") as f:
            json.dump(_INITIAL_STATE, f, indent=2)

        # empty event files
        for fname in ("events.jsonl", "now_playing.json"):
            fpath = data_dir / fname
            with open(fpath, "w"):
                pass  # create empty file

    def _save(self, users: list[dict]) -> None:
        """Write users list to users.json. Direct write (bind-mount safe)."""
        with open(self._registry_path, "w") as f:
            json.dump({"users": users}, f, indent=2)
            f.write("\n")
