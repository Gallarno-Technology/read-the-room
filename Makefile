.PHONY: setup auth up down logs

## Pre-create host-side bind-mount files. Run once before first `make auth`.
setup:
	@[ -f state.json ] || echo '{"last_track_id": null}' > state.json
	@mkdir -p token_cache
	@[ -f .env ] || cp .env.example .env
	@echo "Setup complete. Edit .env with your Spotify credentials, then run: make auth"

## One-time OAuth flow — runs setup_auth.py inside the container (no host Python/pip needed).
## Opens an auth URL; open it on your phone, approve, paste the redirect URL back.
## Token is saved to ./token_cache/ and reused by the daemon on every start.
auth:
	@[ -f state.json ] || echo '{"last_track_id": null}' > state.json
	@mkdir -p token_cache
	docker compose build --quiet
	docker compose run --rm -it daemon python setup_auth.py

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f daemon
