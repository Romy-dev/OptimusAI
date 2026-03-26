.PHONY: help dev up down migrate test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start dev server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up: ## Start all services (Docker)
	docker compose -f deployments/docker-compose.yml up -d

down: ## Stop all services
	docker compose -f deployments/docker-compose.yml down

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	alembic revision --autogenerate -m "$(msg)"

test: ## Run tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=app --cov-report=html

lint: ## Run linter
	ruff check app/ tests/
	ruff format --check app/ tests/

format: ## Format code
	ruff check --fix app/ tests/
	ruff format app/ tests/

typecheck: ## Run mypy
	mypy app/

worker: ## Start ARQ worker
	python -m app.workers.settings

seed: ## Seed database with test data
	python scripts/seed_db.py

superadmin: ## Create superadmin user
	python scripts/create_superadmin.py
