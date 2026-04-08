.PHONY: dev dev-up dev-down api agent dashboard test lint migrate help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Local Development (Docker Compose) ---

dev-up: ## Start all services via Docker Compose
	docker compose up -d

dev-down: ## Stop all services
	docker compose down

dev-logs: ## Tail logs from all services
	docker compose logs -f

# --- Run individually (for development) ---

api: ## Run orchestrator API locally (requires PostgreSQL)
	cd orchestrator && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

agent-scan: ## Run endpoint agent scan
	cd agent && python -m spectis_agent.cli scan

dashboard-dev: ## Run dashboard dev server
	cd dashboard && npm run dev

dashboard-build: ## Build dashboard and copy to orchestrator static
	cd dashboard && npm run build
	cp -r dashboard/dist/* orchestrator/app/static/

# --- Database ---

migrate: ## Run database migrations
	cd orchestrator && alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="add users table")
	cd orchestrator && alembic revision --autogenerate -m "$(msg)"

# --- Testing ---

test: ## Run all tests
	cd orchestrator && python -m pytest tests/ -v
	cd agent && python -m pytest tests/ -v

test-api: ## Run orchestrator tests only
	cd orchestrator && python -m pytest tests/ -v

test-agent: ## Run agent tests only
	cd agent && python -m pytest tests/ -v

# --- Linting ---

lint: ## Run linters
	cd orchestrator && python -m ruff check app/ tests/
	cd agent && python -m ruff check spectis_agent/ tests/

lint-fix: ## Auto-fix lint issues
	cd orchestrator && python -m ruff check --fix app/ tests/
	cd agent && python -m ruff check --fix spectis_agent/ tests/

# --- Docker ---

docker-build: ## Build Docker images
	docker build -t spectis-orchestrator -f orchestrator/Dockerfile .
	docker build -t spectis-agent -f agent/Dockerfile agent/

# --- Helm ---

helm-template: ## Render Helm templates locally
	helm template spectis ./helm/spectis

helm-install: ## Install Helm chart (usage: make helm-install ns=spectis)
	helm install spectis ./helm/spectis -n $(ns) --create-namespace

helm-upgrade: ## Upgrade Helm release
	helm upgrade spectis ./helm/spectis -n $(ns)
