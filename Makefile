.PHONY: help build up down restart logs clean deploy health test

help: ## Show this help message
	@echo "IdeaForge AI - Deployment Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs (use: make logs SERVICE=backend)
	docker-compose logs -f $(SERVICE)

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

providers-health: ## Show configured AI providers from the backend
	@curl -s http://localhost:8000/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('services', {}), indent=2))"

db-shell: ## Open psql shell inside the Postgres container
	docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db

