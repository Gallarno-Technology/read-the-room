.PHONY: setup up down logs

## Pre-create host-side files required by docker-compose bind mounts.
## Run once before first `make up`.
setup:
	@[ -f state.json ] || echo '{"last_track_id": null}' > state.json
	@mkdir -p token_cache
	@[ -f .env ] || cp .env.example .env
	@echo "Setup complete. Edit .env with your Spotify credentials, then run: make up"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f daemon
