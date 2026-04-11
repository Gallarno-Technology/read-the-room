#!/usr/bin/env python3
"""One-time Spotify OAuth setup.

Run this script once on the server (SSH into host, run python setup_auth.py).
It will print an auth URL — open it on your phone, approve in Spotify, then
paste the full redirect URL back into the terminal prompt.

After this runs, the daemon can authenticate headlessly with no further
browser interaction required.
"""
import os
import sys

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

load_dotenv()

REQUIRED_ENV_VARS = [
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URI",
    "SPOTIFY_CACHE_PATH",
]


def main() -> None:
    # Validate all required env vars are present
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your Spotify credentials.")
        sys.exit(1)

    cache_path = os.environ["SPOTIFY_CACHE_PATH"]
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)

    cache_handler = CacheFileHandler(cache_path=cache_path)
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope="user-read-playback-state user-read-currently-playing user-modify-playback-state",
        open_browser=False,  # D-01: print URL, do not auto-open browser
        cache_handler=cache_handler,
    )

    # D-01: Print auth URL for the user to open on their phone
    auth_url = auth_manager.get_authorize_url()
    print("\nOpen this URL in a browser (e.g. on your phone) and approve access:")
    print(f"\n  {auth_url}\n")

    redirect_response = input("Paste the full redirect URL here: ").strip()
    if not redirect_response:
        print("ERROR: No redirect URL provided. Exiting.")
        sys.exit(1)

    # Exchange authorization code for access + refresh tokens (saved to cache)
    code = auth_manager.parse_response_code(redirect_response)
    auth_manager.get_access_token(code, as_dict=False)

    # D-02: Validate token with one test API call
    sp = spotipy.Spotify(auth_manager=auth_manager)
    try:
        user = sp.current_user()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Token obtained but API call failed: {exc}")
        sys.exit(1)

    display_name = user.get("display_name") or user.get("id", "unknown")
    print(f"\nAuth successful. Logged in as: {display_name}")
    print(f"Token saved to: {cache_path}")
    print("\nThe daemon can now run headlessly. Start it with: docker compose up -d")


if __name__ == "__main__":
    main()
