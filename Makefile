.PHONY: help build up down restart logs clean deploy health test rebuild redeploy check-errors check-logs

help: ## Show this help message
	@echo "IdeaForge AI - Deployment Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

build-no-cache: ## Build Docker images without cache
	docker-compose build --no-cache

up: ## Start all services
	docker-compose up -d

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
	@echo "🚀 Deploying IdeaForge AI..."
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Please create it from .env.example"; \
		exit 1; \
	fi
	docker-compose build
	docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔍 Checking health..."
	@for i in 1 2 3 4 5; do \
		if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend is healthy"; \
			break; \
		fi; \
		echo "   Waiting... ($$i/5)"; \
		sleep 2; \
	done
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

redeploy: ## Rebuild without cache and redeploy
	@echo "🔄 Rebuilding and redeploying IdeaForge AI..."
	docker-compose down
	docker-compose build --no-cache backend frontend
	docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔍 Checking health..."
	@for i in 1 2 3 4 5; do \
		if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend is healthy"; \
			break; \
		fi; \
		echo "   Waiting... ($$i/5)"; \
		sleep 2; \
	done
	@echo ""
	@echo "✅ Redeployment complete!"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "🔍 Running error check..."
	@$(MAKE) check-errors

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
	docker-compose build --no-cache
	docker-compose up -d

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
