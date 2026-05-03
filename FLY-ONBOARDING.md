# Onboarding a User on the Fly.io Deployment

These steps create a new user on the live `read-the-room.fly.dev` instance. The user registry on the Fly machine starts empty; every user must be onboarded once before they can sign in at `/login`.

## Prerequisites

- `flyctl` installed locally and authenticated (`flyctl auth login`).
- The Spotify developer app for this deployment must have `https://read-the-room.fly.dev/auth/callback` listed in its **Redirect URIs**. Without it, the OAuth callback fails.
- The app currently caps the registry at 5 users (`MAX_USERS` in `user_registry.py`).

## Steps

1. **Open a shell on the Fly machine.**
   ```bash
   flyctl ssh console -a read-the-room
   ```

2. **Generate the OAuth URL.** Inside the SSH session:
   ```bash
   cd /app
   python scripts/manage_users.py generate-url <name>
   ```
   Replace `<name>` with a label for the user (any string — used only for the operator's reference). The script prints:
   - A `UID` (the access code the user will paste into `/login`).
   - A Spotify authorization URL with the UID baked into the `state` parameter.

   The user's status is `pending` at this point — the UID will not work at `/login` yet.

3. **Open the printed URL in a browser** and complete the Spotify authorization. Spotify redirects to `https://read-the-room.fly.dev/auth/callback`, which:
   - Validates the `state` parameter against the pending user.
   - Exchanges the auth code for an access token and writes it to `/data/users/<uid>/token_cache/.cache`.
   - Flips the user's status to `active`.
   - Spawns the per-user daemon so polling starts immediately.
   - Sets the `uid` cookie and redirects to the dashboard.

4. **Sign in at `/login`** using the UID as the access code. After the OAuth redirect in step 3 the cookie is already set, so the dashboard loads directly. On a different browser or device, paste the UID into `/login`.

## Verifying

From the Fly SSH session:
```bash
cd /app
python scripts/manage_users.py list
```
Active users show `status: active`. A user that completed the OAuth redirect should appear here.

## Removing a User

```bash
flyctl ssh console -a read-the-room
cd /app
python scripts/manage_users.py remove <uid>
```
This stops the user's daemon (SIGTERM via PID file) and deletes their `/data/users/<uid>/` directory.

## Notes

- The registry (`/data/users.json`) and per-user state live on a Fly volume, so users survive deploys.
- `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are stored as Fly secrets (`flyctl secrets list -a read-the-room`); `SPOTIFY_REDIRECT_URI` is set in `fly.toml`.
