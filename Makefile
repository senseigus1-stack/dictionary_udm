.PHONY: dev down logs test lint format migrate import-dictionary helm-lint

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api bot worker

test:
	pytest -q --cov=backend/app --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

migrate:
	alembic -c backend/alembic.ini upgrade head

import-dictionary:
	PYTHONPATH=backend python -m app.cli import-dictionary udmurt_dictionary_full.json

helm-lint:
	helm lint deploy/helm
