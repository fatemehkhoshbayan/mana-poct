.PHONY: up down logs test seed fmt migrate revision shell-backend kafka-up

build:
	docker compose up --build
	
up:
	docker compose up

kafka-up:
	docker compose --profile kafka up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd back-end && uv run pytest

seed:
	docker compose exec backend uv run python -m app.mock_db.seed

fmt:
	cd back-end && uv run ruff format .
	cd front-end && npm run prettier

migrate:
	docker compose exec backend uv run alembic upgrade head

revision:
	docker compose exec backend uv run alembic revision --autogenerate -m "$(msg)"

shell-backend:
	docker compose exec backend /bin/bash
