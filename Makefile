.PHONY: setup auth up down logs fsm-on fsm-off fsm-status

## Pre-create host-side bind-mount files. Run once before first `make auth`.
setup:
	@[ -f state.json ] || echo '{"last_track_id": null}' > state.json
	@mkdir -p token_cache
	@[ ! -f lyrics_cache.db ] || sudo rm -f lyrics_cache.db
	@touch lyrics_cache.db
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

## Family Safe Mode toggle (D-05). Merges into existing state.json — does not overwrite other keys.
## Runs inside the container so the same bind-mounted state.json path is used.
fsm-on:
	@docker compose exec daemon python -c "import json; s=json.load(open('state.json')); s['family_safe_mode']=True; json.dump(s, open('state.json','w')); print('Family Safe Mode: ON')"

fsm-off:
	@docker compose exec daemon python -c "import json; s=json.load(open('state.json')); s['family_safe_mode']=False; json.dump(s, open('state.json','w')); print('Family Safe Mode: OFF')"

fsm-status:
	@docker compose exec daemon python -c "import json; s=json.load(open('state.json')); print('Family Safe Mode:', 'ON' if s.get('family_safe_mode', False) else 'OFF')"
