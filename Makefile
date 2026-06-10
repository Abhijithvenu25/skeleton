.PHONY: help install sync up down logs shell ps migrate revision test test-unit test-int lint format typecheck seed clean reset

PYTHON ?= python
DC     ?= docker compose

help:
	@echo "Targets:"
	@echo "  install      Install deps via uv"
	@echo "  up           Bring up app, postgres, redis"
	@echo "  down         Stop services"
	@echo "  logs         Tail logs"
	@echo "  shell        Open a shell in the app container"
	@echo "  ps           List running services"
	@echo "  migrate      Apply Alembic migrations"
	@echo "  revision m=  Create a new migration (provide m=\"message\")"
	@echo "  seed         Seed dev data (admin user)"
	@echo "  test         Run full test suite"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-int     Run integration tests (requires compose up)"
	@echo "  lint         Run ruff"
	@echo "  format       Run ruff format"
	@echo "  typecheck    Run mypy"
	@echo "  clean        Remove caches"
	@echo "  reset        Tear down services and volumes"

install:
	uv sync --all-extras

sync:
	uv sync --all-extras

up:
	$(DC) up -d --build
	@echo "Waiting for app to become ready..."
	@$(DC) exec -T app ./scripts/wait-for.sh

down:
	$(DC) down

logs:
	$(DC) logs -f --tail=200

shell:
	$(DC) exec app bash

ps:
	$(DC) ps

migrate:
	$(DC) exec app alembic upgrade head

revision:
	@test -n "$(m)" || (echo "Usage: make revision m=\"message\""; exit 1)
	$(DC) exec app alembic revision --autogenerate -m "$(m)"

seed:
	$(DC) exec app python -m scripts.seed

test:
	uv run pytest -q

test-unit:
	uv run pytest -q tests/unit

test-int:
	uv run pytest -q tests/integration

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy src

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

reset:
	$(DC) down -v
