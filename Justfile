# KubeMind task orchestration

default:
    @just --list

# --- Dev ---

# Run backend + frontend locally (use separate terminals for each)
dev: backend-dev frontend-dev

# Run FastAPI backend with hot reload
backend-dev:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Next.js frontend
frontend-dev:
    cd frontend && pnpm dev

# Run RQ worker
worker:
    rq worker --url "$(REDIS_URL)" kubemind

# Run RQ scheduler
scheduler:
    rqscheduler --url "$(REDIS_URL)" --interval 60

# --- Docker ---

# Run full stack via docker-compose
up:
    docker compose up -d

# Stop docker-compose stack
down:
    docker compose down

# Rebuild docker images
build:
    docker compose build

# Logs
logs:
    docker compose logs -f

# --- Test ---

# Run all Python tests
test: test-unit test-integration

# Unit tests (fast, no IO)
test-unit:
    pytest -m unit

# Integration tests (testcontainers: real Postgres + Redis)
test-integration:
    pytest -m integration

# E2E tests (Playwright, full stack)
test-e2e:
    pytest -m e2e

# Frontend tests
test-frontend:
    cd frontend && pnpm test

# --- Lint / Typecheck ---

# Lint + format check (Python + TS)
lint: lint-py lint-ts

lint-py:
    ruff check .
    ruff format --check .
    mypy .

lint-ts:
    cd frontend && pnpm lint

# Fix formatting
format:
    ruff format .
    ruff check --fix .
    cd frontend && pnpm format

# Typecheck
typecheck: mypy frontend-typecheck

mypy:
    mypy .

frontend-typecheck:
    cd frontend && pnpm typecheck

# --- DB ---

# Run Alembic migration
migrate:
    alembic upgrade head

# Create new migration
migration name:
    alembic revision --autogenerate -m "{{name}}"

# Rollback last migration
migrate-rollback:
    alembic downgrade -1

# --- Cluster (dev) ---

# Create ephemeral kind cluster for dev
cluster-up:
    kind create cluster --name kubemind-dev

# Delete dev kind cluster
cluster-down:
    kind delete cluster --name kubemind-dev

# --- Install deps ---

install: install-py install-ts

install-py:
    uv sync --all-extras

install-ts:
    cd frontend && pnpm install

# --- Clean ---

clean:
    rm -rf .pytest_cache .mypy_cache .ruff_cache
    cd frontend && rm -rf node_modules .next
    find . -type d -name __pycache__ -exec rm -rf {} +
