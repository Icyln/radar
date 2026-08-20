.PHONY: backend-install backend-test backend-lint backend-format backend-run frontend-install frontend-lint frontend-typecheck frontend-build migrate monitor monitor-high monitor-normal monitor-low monitor-watchlist monitor-registry scheduled-smoke telegram-webhook seed-cloudflare

backend-install:
	cd backend && python -m pip install -e '.[dev]'

backend-test:
	cd backend && pytest

backend-lint:
	cd backend && ruff check .

backend-format:
	cd backend && ruff format .

backend-run:
	cd backend && uvicorn app.main:app --reload

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-build:
	cd frontend && npm run build

migrate:
	cd backend && alembic upgrade head

monitor:
	cd backend && python -m app.workers.monitor

monitor-high:
	cd backend && python -m app.workers.monitor --priority high

monitor-normal:
	cd backend && python -m app.workers.monitor --priority normal

monitor-low:
	cd backend && python -m app.workers.monitor --priority low

monitor-watchlist:
	cd backend && python -m app.workers.monitor --scope watchlist --batch-size 50 --max-concurrency 3

monitor-registry:
	cd backend && python -m app.workers.monitor --scope registry --batch-size 50 --max-concurrency 3

scheduled-smoke:
	cd backend && python -m app.scripts.check_worker_config --require-telegram --require-remote-database

telegram-webhook:
	cd backend && python -m app.scripts.set_telegram_webhook

seed-cloudflare:
	cd backend && python -m app.scripts.seed_company --provider greenhouse --name "Cloudflare" --ats-identifier cloudflare --website "https://www.cloudflare.com" --career-url "https://www.cloudflare.com/careers/" --priority high
