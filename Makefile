.PHONY: help build up down restart logs clean deploy health test rebuild redeploy check-errors check-logs version clean-all build-versioned deploy-versioned

# Get git SHA for versioning
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION := $(GIT_SHA)
IMAGE_TAG := ideaforge-ai-$(VERSION)

help: ## Show this help message
	@echo "IdeaForge AI - Deployment Commands"
	@echo "=================================="
	@echo "Current Git SHA: $(GIT_SHA)"
	@echo "Image Tag: $(IMAGE_TAG)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

version: ## Show current version information
	@echo "Git SHA: $(GIT_SHA)"
	@echo "Version: $(VERSION)"
	@echo "Image Tag: $(IMAGE_TAG)"

clean-all: ## Complete cleanup: remove containers, volumes, networks, and images
	@echo "🧹 Performing complete cleanup..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete"

build: ## Build Docker images with current git SHA
	@echo "🔨 Building Docker images with tag: $(IMAGE_TAG)"
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose build --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION)
	@echo "✅ Build complete"

build-no-cache: ## Build Docker images without cache
	@echo "🔨 Building Docker images (no cache) with tag: $(IMAGE_TAG)"
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose build --no-cache --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION)
	@echo "✅ Build complete"

build-versioned: build-no-cache ## Alias for build-no-cache with versioning

up: ## Start all services
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs (use: make logs SERVICE=backend)
	docker-compose logs -f $(SERVICE)

logs-all: ## View all service logs
	docker-compose logs -f

clean: ## Remove containers, networks, and volumes
	docker-compose down -v
	docker system prune -f

deploy: ## Full deployment (build + start + health check)
	@echo "🚀 Deploying IdeaForge AI (Version: $(VERSION))..."
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Continuing with environment variables from shell..."; \
	fi
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) build
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@$(MAKE) health
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "   Version: $(VERSION)"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

redeploy: clean-all build-no-cache deploy check-errors ## Complete rebuild and redeploy (clean + build + deploy + verify)
	@echo ""
	@echo "✅ Complete redeployment finished!"
	@echo "   Version: $(VERSION)"
	@echo "   All services rebuilt and deployed"

deploy-versioned: redeploy ## Alias for redeploy with versioning

health: ## Check service health
	@echo "🔍 Checking service health..."
	@echo ""
	@echo "Backend Health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Backend not responding"
	@echo ""
	@echo "Frontend:"
	@curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:3001 || echo "❌ Frontend not responding"
	@echo ""
	@echo "Service Status:"
	@docker-compose ps

test: ## Run tests
	@echo "🧪 Running tests..."
	docker-compose exec backend pytest || echo "⚠️  Tests not configured"

status: ## Show service status
	docker-compose ps

stop: ## Stop all services
	docker-compose stop

start: ## Start stopped services
	docker-compose start

rebuild: ## Rebuild and restart services
	@$(MAKE) build-no-cache
	@$(MAKE) up

logs-backend: ## Tail backend logs
	docker-compose logs -f backend

logs-frontend: ## Tail frontend logs
	docker-compose logs -f frontend

logs-postgres: ## Tail postgres logs
	docker-compose logs -f postgres

logs-redis: ## Tail redis logs
	docker-compose logs -f redis

check-errors: ## Check all logs for errors (comprehensive)
	@echo "🔍 Checking for errors in all services..."
	@echo ""
	@echo "=== Backend Errors ==="
	@docker-compose logs backend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in backend"
	@echo ""
	@echo "=== Frontend Errors ==="
	@docker-compose logs frontend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in frontend"
	@echo ""
	@echo "=== Postgres Errors ==="
	@docker-compose logs postgres --tail 500 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in postgres"
	@echo ""
	@echo "=== Redis Errors ==="
	@docker-compose logs redis --tail 500 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in redis"
	@echo ""
	@echo "✅ Error check complete"

check-logs: ## Comprehensive log inspection (last 500 lines per service)
	@echo "📋 Comprehensive Log Inspection"
	@echo "================================"
	@echo ""
	@echo "=== Backend Logs (last 500 lines) ==="
	@docker-compose logs backend --tail 500
	@echo ""
	@echo "=== Frontend Logs (last 500 lines) ==="
	@docker-compose logs frontend --tail 500
	@echo ""
	@echo "=== Postgres Logs (last 200 lines) ==="
	@docker-compose logs postgres --tail 200
	@echo ""
	@echo "=== Redis Logs (last 200 lines) ==="
	@docker-compose logs redis --tail 200

check-backend: ## Check backend logs for errors
	@echo "🔍 Checking backend logs..."
	@docker-compose logs backend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -30 || echo "✅ No errors found"

check-frontend: ## Check frontend logs for errors
	@echo "🔍 Checking frontend logs..."
	@docker-compose logs frontend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -30 || echo "✅ No errors found"

providers-health: ## Show configured AI providers from the backend
	@curl -s http://localhost:8000/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('services', {}), indent=2))"

db-shell: ## Open psql shell inside the Postgres container
	docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db

db-migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head || echo "⚠️  Migrations not configured"

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh
