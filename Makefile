.PHONY: setup up down restart logs ui-logs daemon-logs

## Pre-create host-side bind-mount files. Run once before first start.
setup:
	@[ -f state.json ] || echo '{"last_track_id": null}' > state.json
	@mkdir -p token_cache data
	@[ ! -d lyrics_cache.db ] || sudo rm -rf lyrics_cache.db
	@[ ! -f lyrics_cache.db ] || sudo rm -f lyrics_cache.db
	@touch lyrics_cache.db
	@[ -f .env ] || cp .env.example .env
	@echo "Setup complete. Edit .env with your Spotify credentials, then start: make up"

up:
	docker compose up -d

down:
	docker compose down

## Stop containers and rebuild/start with latest code changes.
restart:
	docker compose down
	docker compose up -d --build

## Tail all container logs
logs:
	docker compose logs -f

## Tail web_ui container logs (FastAPI/uvicorn on port 8888)
ui-logs:
	docker compose logs -f web_ui

## Tail daemon container logs (Spotify poll loop)
daemon-logs:
	docker compose logs -f daemon
