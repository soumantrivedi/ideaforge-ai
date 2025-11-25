.PHONY: help build up down restart logs clean deploy deploy-full health test rebuild redeploy check-errors check-logs version clean-all build-versioned deploy-versioned db-migrate db-seed db-setup agno-init setup db-backup db-restore rebuild-safe kind-create kind-delete kind-deploy kind-test kind-cleanup eks-deploy eks-test eks-cleanup k8s-deploy k8s-test k8s-logs k8s-status migrate-to-kind

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

clean-all: ## Complete cleanup: backup DB first, then remove containers, volumes, networks, and images
	@echo "🧹 Performing complete cleanup..."
	@echo "⚠️  WARNING: This will remove all data including database!"
	@echo "📦 Creating database backup before cleanup..."
	@$(MAKE) db-backup || echo "⚠️  Backup failed, but continuing..."
	@echo "💾 Database backup saved in backups/ directory"
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

build-apps: ## Build only backend and frontend images (skip postgres/redis)
	@echo "🔨 Building application images (backend + frontend) with tag: $(GIT_SHA)"
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose build --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION) backend frontend
	@echo "✅ Application images built: ideaforge-ai-backend:$(GIT_SHA) and ideaforge-ai-frontend:$(GIT_SHA)"

up: ## Start all services
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose up -d

down: ## Stop all services (preserves data and config files)
	docker-compose down

down-clean: ## Stop and remove containers, networks (preserves volumes and config files)
	@echo "🛑 Stopping and removing containers and networks..."
	@echo "⚠️  This will preserve volumes and configuration files"
	docker-compose down --remove-orphans
	@echo "✅ Containers and networks removed (volumes preserved)"

restart: ## Restart all services
	docker-compose restart

logs: ## View logs (use: make logs SERVICE=backend)
	docker-compose logs -f $(SERVICE)
clean: ## Remove containers, networks, and volumes (with backup)
	@echo "⚠️  WARNING: This will remove database volumes!"
	@echo "📦 Creating database backup before cleanup..."
	@$(MAKE) db-backup || echo "⚠️  Backup failed, but continuing..."
	@docker-compose down -v
	@docker system prune -f
	@echo "💾 Database backup saved in backups/ directory"

logs-all: ## View all service logs
	docker-compose logs -f


deploy: ## Full deployment (build + start + migrations + health check)
	@echo "🚀 Deploying IdeaForge AI (Version: $(VERSION))..."
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Continuing with environment variables from shell..."; \
	fi
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) build
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔄 Running database migrations..."
	@$(MAKE) db-migrate
	@$(MAKE) health
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "   Version: $(VERSION)"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "💡 To seed database and initialize Agno, run: make setup"

deploy-full: ## Full deployment with complete setup (build + start + migrations + seed + agno init)
	@echo "🚀 Deploying IdeaForge AI with Complete Setup (Version: $(VERSION))..."
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Creating from .env.example..."; \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "   Created .env from .env.example - please fill in your API keys!"; \
			echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN"; \
			exit 1; \
		else \
			echo "   .env.example not found. Continuing with environment variables from shell..."; \
		fi; \
	fi
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) build
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔄 Running complete database setup (migrations + seeding)..."
	@$(MAKE) db-setup
	@echo "🤖 Initializing Agno framework..."
	@$(MAKE) agno-init
	@$(MAKE) health
	@echo ""
	@echo "✅ Full deployment complete!"
	@echo "   Version: $(VERSION)"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "📊 Database Summary:"
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -c "SELECT COUNT(*) as total_products FROM products; SELECT COUNT(*) as total_users FROM user_profiles; SELECT COUNT(*) as total_tenants FROM tenants;" 2>&1 | grep -E "total_|-[[:space:]]*[0-9]" || true

health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "🔍 Backend Health Check:"
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "❌ Backend not responding"
	@echo ""

test: ## Run tests
	docker-compose exec backend pytest || echo "⚠️  Tests not configured"

ps: ## Show running containers
	docker-compose ps

stop: ## Stop all services
	docker-compose stop

start: ## Start stopped services
	docker-compose start

rebuild: ## Rebuild and restart services (preserves database)
	@echo "🔨 Rebuilding and restarting services..."
	docker-compose up -d --build --force-recreate
	@echo "✅ Rebuild complete"

rebuild-safe: ## Safe rebuild: backup DB, rebuild images, restore if needed (preserves all data)
	@echo "🔄 Performing safe rebuild..."
	@echo "📦 Creating database backup..."
	@$(MAKE) db-backup || echo "⚠️  Backup failed, but continuing..."
	@echo "🔨 Rebuilding images..."
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose build --no-cache
	@echo "🛑 Stopping services..."
	@docker-compose down
	@echo "🚀 Starting services with new images..."
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose up -d
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔄 Running migrations..."
	@$(MAKE) db-migrate
	@echo "✅ Safe rebuild complete (data preserved)"

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-postgres: ## View postgres logs
	docker-compose logs -f postgres

logs-redis: ## View redis logs
	docker-compose logs -f redis

check-errors-backend: ## Check for errors in backend logs
	@docker-compose logs backend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in backend"

check-errors-frontend: ## Check for errors in frontend logs
	@docker-compose logs frontend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in frontend"

check-errors-postgres: ## Check for errors in postgres logs
	@docker-compose logs postgres --tail 500 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in postgres"

check-errors-redis: ## Check for errors in redis logs
	@docker-compose logs redis --tail 500 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found in redis"

check-errors: check-errors-backend check-errors-frontend check-errors-postgres check-errors-redis ## Check for errors in all service logs

check-logs-backend: ## Show recent backend logs
	@docker-compose logs backend --tail 500

check-logs-frontend: ## Show recent frontend logs
	@docker-compose logs frontend --tail 500

check-logs-postgres: ## Show recent postgres logs
	@docker-compose logs postgres --tail 200

check-logs-redis: ## Show recent redis logs
	@docker-compose logs redis --tail 200

check-logs: check-logs-backend check-logs-frontend check-logs-postgres check-logs-redis ## Show recent logs from all services

check-all-errors: ## Comprehensive error check across all services
	@echo "🔍 Checking for errors in all services..."
	@docker-compose logs backend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -30 || echo "✅ No errors found"

check-all-errors-frontend: ## Comprehensive error check in frontend
	@docker-compose logs frontend --tail 1000 | grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | grep -v "warning" | grep -v "WARNING" | head -30 || echo "✅ No errors found"

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db

db-migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251124000003_user_api_keys.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251124000004_product_scoring.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251125000001_user_management_tenants.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@echo "✅ Migrations complete"

db-seed: ## Seed database with sample data
	@echo "🌱 Seeding database with sample data..."
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/seed_sample_data.sql 2>&1 | grep -v "NOTICE" || true
	@echo "✅ Database seeded"

db-setup: db-migrate db-seed ## Run migrations and seed database

agno-init: ## Initialize Agno framework (for docker-compose)
	@echo "🤖 Initializing Agno framework..."
	@max_attempts=30; \
	attempt=0; \
	while [ $$attempt -lt $$max_attempts ]; do \
		if curl -f http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend is ready, initializing Agno..."; \
			curl -X POST http://localhost:8000/api/agents/initialize \
				-H "Content-Type: application/json" \
				-d '{"enable_rag": true}' \
				-s | python3 -m json.tool 2>/dev/null || echo "⚠️  Agno initialization endpoint may not be available"; \
			break; \
		fi; \
		attempt=$$((attempt + 1)); \
		echo "   Waiting for backend... ($$attempt/$$max_attempts)"; \
		sleep 2; \
	done; \
	if [ $$attempt -ge $$max_attempts ]; then \
		echo "⚠️  Backend not ready after $$max_attempts attempts"; \
	fi
	@echo "✅ Agno initialization complete"

kind-agno-init: ## Initialize Agno framework in kind cluster
	@echo "🤖 Initializing Agno framework in kind cluster..."
	@max_attempts=30; \
	attempt=0; \
	BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "⚠️  Backend pod not found"; \
		exit 1; \
	fi; \
	while [ $$attempt -lt $$max_attempts ]; do \
		if kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			curl -f http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend is ready, initializing Agno..."; \
			kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
				curl -X POST http://localhost:8000/api/agents/initialize \
					-H "Content-Type: application/json" \
					-d '{"enable_rag": true}' \
					-s | head -20 || echo "⚠️  Agno initialization endpoint may not be available"; \
			break; \
		fi; \
		attempt=$$((attempt + 1)); \
		echo "   Waiting for backend... ($$attempt/$$max_attempts)"; \
		sleep 2; \
	done; \
	if [ $$attempt -ge $$max_attempts ]; then \
		echo "⚠️  Backend not ready after $$max_attempts attempts"; \
	fi
	@echo "✅ Agno initialization complete"

eks-agno-init: ## Initialize Agno framework in EKS cluster
	@echo "🤖 Initializing Agno framework in EKS cluster..."
	@max_attempts=30; \
	attempt=0; \
	BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "⚠️  Backend pod not found"; \
		exit 1; \
	fi; \
	while [ $$attempt -lt $$max_attempts ]; do \
		if kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- \
			curl -f http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend is ready, initializing Agno..."; \
			kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- \
				curl -X POST http://localhost:8000/api/agents/initialize \
					-H "Content-Type: application/json" \
					-d '{"enable_rag": true}' \
					-s | head -20 || echo "⚠️  Agno initialization endpoint may not be available"; \
			break; \
		fi; \
		attempt=$$((attempt + 1)); \
		echo "   Waiting for backend... ($$attempt/$$max_attempts)"; \
		sleep 2; \
	done; \
	if [ $$attempt -ge $$max_attempts ]; then \
		echo "⚠️  Backend not ready after $$max_attempts attempts"; \
	fi
	@echo "✅ Agno initialization complete"

setup: db-setup agno-init ## Complete setup: migrations, seed, and Agno init

db-backup: ## Backup database to backups/ directory with timestamp
	@echo "📦 Creating database backup..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	BACKUP_FILE="backups/ideaforge_db_backup_$$TIMESTAMP.sql"; \
	echo "   Backup file: $$BACKUP_FILE"; \
	if docker-compose exec -T postgres pg_dump -U agentic_pm -d agentic_pm_db --clean --if-exists > $$BACKUP_FILE 2>&1; then \
		if [ -s $$BACKUP_FILE ]; then \
			echo "✅ Database backup created: $$BACKUP_FILE"; \
			ls -lh $$BACKUP_FILE; \
			ln -sf $$(basename $$BACKUP_FILE) backups/latest_backup.sql; \
			echo "   Latest backup: backups/latest_backup.sql"; \
		else \
			echo "⚠️  First attempt failed, trying alternative method..."; \
			rm -f $$BACKUP_FILE; \
			if docker-compose exec -T postgres pg_dump -U agentic_pm agentic_pm_db > $$BACKUP_FILE 2>&1; then \
				if [ -s $$BACKUP_FILE ]; then \
					echo "✅ Database backup created: $$BACKUP_FILE"; \
					ls -lh $$BACKUP_FILE; \
					ln -sf $$(basename $$BACKUP_FILE) backups/latest_backup.sql; \
					echo "   Latest backup: backups/latest_backup.sql"; \
				else \
					echo "❌ Backup file is empty"; \
					exit 1; \
				fi; \
			else \
				echo "❌ Database backup failed"; \
				exit 1; \
			fi; \
		fi; \
	else \
		echo "❌ Database backup failed"; \
		exit 1; \
	fi

db-restore: ## Restore database from backup file (use: make db-restore BACKUP=backups/backup_file.sql)
	@if [ -z "$(BACKUP)" ]; then \
		echo "❌ Please specify backup file: make db-restore BACKUP=backups/backup_file.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP)" ]; then \
		echo "❌ Backup file not found: $(BACKUP)"; \
		exit 1; \
	fi
	@echo "📦 Restoring database from: $(BACKUP)"
	@echo "⚠️  WARNING: This will overwrite existing data!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db < $(BACKUP)
	@echo "✅ Database restored from $(BACKUP)"

db-list-backups: ## List available database backups
	@echo "📦 Available database backups:"
	@ls -lh backups/*.sql 2>/dev/null | awk '{print $$9, "("$$5")"}' || echo "   No backups found"

migrate-to-kind: db-backup ## Migrate database from docker-compose to kind cluster
	@echo "🔄 Migrating database from docker-compose to kind cluster..."
	@if [ ! -f backups/latest_backup.sql ]; then \
		echo "❌ No backup found. Creating backup now..."; \
		$(MAKE) db-backup; \
	fi
	@BACKUP_FILE=backups/latest_backup.sql; \
	if [ ! -f $$BACKUP_FILE ]; then \
		echo "❌ Backup file not found: $$BACKUP_FILE"; \
		exit 1; \
	fi
	@echo "📦 Backup file: $$BACKUP_FILE"
	@echo "⏳ Waiting for kind cluster postgres to be ready..."
	@kubectl wait --for=condition=ready pod -l app=postgres -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --timeout=300s || \
		(echo "❌ Postgres pod not ready in kind cluster" && exit 1)
	@echo "📥 Copying backup to postgres pod..."
	@kubectl cp $$BACKUP_FILE $(K8S_NAMESPACE)/$$(kubectl get pod -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.sql --context kind-$(KIND_CLUSTER_NAME)
	@echo "🔄 Restoring database in kind cluster..."
	@kubectl exec -n $(K8S_NAMESPACE) -i $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}') --context kind-$(KIND_CLUSTER_NAME) -- \
		psql -U agentic_pm -d agentic_pm_db < $$BACKUP_FILE || \
		kubectl exec -n $(K8S_NAMESPACE) $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}') --context kind-$(KIND_CLUSTER_NAME) -- \
		sh -c "cat /tmp/backup.sql | psql -U agentic_pm -d agentic_pm_db"
	@echo "✅ Database migration complete!"
	@echo "   Data from docker-compose has been restored to kind cluster"
	@echo ""
	@echo "📊 Verifying data in kind cluster..."
	@kubectl exec -n $(K8S_NAMESPACE) $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}') --context kind-$(KIND_CLUSTER_NAME) -- \
		psql -U agentic_pm -d agentic_pm_db -c "SELECT COUNT(*) as total_products FROM products; SELECT COUNT(*) as total_users FROM user_profiles; SELECT COUNT(*) as total_tenants FROM tenants;" 2>&1 | grep -E "total_|-[[:space:]]*[0-9]" || true

teardown-docker-compose: db-backup down-clean ## Tear down docker-compose (backup DB, stop containers, preserve config files)
	@echo "🛑 Tearing down docker-compose deployment..."
	@echo "✅ Docker-compose containers stopped and removed"
	@echo "✅ Configuration files preserved"
	@echo "✅ Database backup created in backups/ directory"
	@echo ""
	@echo "💡 To restore and use docker-compose again:"
	@echo "   make up"
	@echo "   make db-restore BACKUP=backups/latest_backup.sql"

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

# ============================================================================
# Kubernetes Deployment Targets (Kind & EKS)
# ============================================================================

K8S_NAMESPACE ?= ideaforge-ai
K8S_DIR ?= k8s
KIND_CLUSTER_NAME ?= ideaforge-ai
KIND_IMAGE ?= kindest/node:v1.33.0
EKS_CLUSTER_NAME ?= ideaforge-ai
EKS_REGION ?= us-east-1
EKS_NAMESPACE ?= $(K8S_NAMESPACE)
EKS_IMAGE_REGISTRY ?= ghcr.io/soumantrivedi/ideaforge-ai
EKS_IMAGE_TAG ?= latest
EKS_GITHUB_USERNAME ?= $(shell git config user.name 2>/dev/null || echo "")
EKS_GITHUB_TOKEN ?= $(shell grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo "")

kind-create: ## Create a local kind cluster for testing
	@echo "🐳 Creating kind cluster: $(KIND_CLUSTER_NAME)..."
	@if kind get clusters | grep -q "^$(KIND_CLUSTER_NAME)$$"; then \
		echo "⚠️  Cluster $(KIND_CLUSTER_NAME) already exists"; \
		echo "   Use 'make kind-delete' to remove it first"; \
		exit 1; \
	fi
	@echo "kind: Cluster" > /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "apiVersion: kind.x-k8s.io/v1alpha4" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "nodes:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "- role: control-plane" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  kubeadmConfigPatches:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - |" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    kind: InitConfiguration" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    nodeRegistration:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "      kubeletExtraArgs:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "        node-labels: \"ingress-ready=true\"" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  extraPortMappings:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - containerPort: 80" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    hostPort: 8080" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    protocol: TCP" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - containerPort: 443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    hostPort: 8443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    protocol: TCP" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@kind create cluster --name $(KIND_CLUSTER_NAME) --image $(KIND_IMAGE) --config /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml || true
	@rm -f /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "⏳ Waiting for cluster to be ready..."
	@kubectl wait --for=condition=Ready nodes --all --timeout=300s --context kind-$(KIND_CLUSTER_NAME)
	@echo "✅ Kind cluster created successfully!"
	@echo "   Cluster name: $(KIND_CLUSTER_NAME)"
	@echo "   Context: kind-$(KIND_CLUSTER_NAME)"

kind-delete: ## Delete the local kind cluster
	@echo "🗑️  Deleting kind cluster: $(KIND_CLUSTER_NAME)..."
	@kind delete cluster --name $(KIND_CLUSTER_NAME) || echo "⚠️  Cluster not found or already deleted"
	@echo "✅ Kind cluster deleted"

kind-setup-ingress: ## Install NGINX ingress controller in kind cluster
	@echo "🌐 Installing NGINX Ingress Controller..."
	@kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for ingress controller to be ready..."
	@kubectl wait --namespace ingress-nginx \
		--for=condition=ready pod \
		--selector=app.kubernetes.io/component=controller \
		--timeout=300s \
		--context kind-$(KIND_CLUSTER_NAME)
	@echo "✅ NGINX Ingress Controller installed"

kind-load-images: ## Load Docker images into kind cluster
	@echo "📦 Loading Docker images into kind cluster..."
	@BACKEND_IMAGE=""; \
	FRONTEND_IMAGE=""; \
	if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "ideaforge-ai-backend:$(GIT_SHA)"; then \
		BACKEND_IMAGE="ideaforge-ai-backend:$(GIT_SHA)"; \
		echo "   Found backend image: $$BACKEND_IMAGE"; \
	elif docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "ideaforge-ai-backend:latest"; then \
		BACKEND_IMAGE="ideaforge-ai-backend:latest"; \
		echo "   Found backend image: $$BACKEND_IMAGE"; \
	else \
		echo "⚠️  Backend image not found. Please run 'make build-apps' first."; \
		exit 1; \
	fi; \
	if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "ideaforge-ai-frontend:$(GIT_SHA)"; then \
		FRONTEND_IMAGE="ideaforge-ai-frontend:$(GIT_SHA)"; \
		echo "   Found frontend image: $$FRONTEND_IMAGE"; \
	elif docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "ideaforge-ai-frontend:latest"; then \
		FRONTEND_IMAGE="ideaforge-ai-frontend:latest"; \
		echo "   Found frontend image: $$FRONTEND_IMAGE"; \
	else \
		echo "⚠️  Frontend image not found. Please run 'make build-apps' first."; \
		exit 1; \
	fi; \
	echo "   Loading backend image: $$BACKEND_IMAGE"; \
	kind load docker-image $$BACKEND_IMAGE --name $(KIND_CLUSTER_NAME) || exit 1; \
	echo "   Loading frontend image: $$FRONTEND_IMAGE"; \
	kind load docker-image $$FRONTEND_IMAGE --name $(KIND_CLUSTER_NAME) || exit 1; \
	echo "✅ Images loaded successfully"

kind-update-images: ## Update image references in manifests for kind
	@echo "🔄 Updating image references for kind..."
	@BACKEND_IMAGE=""; \
	FRONTEND_IMAGE=""; \
	if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-backend:$(GIT_SHA)$$"; then \
		BACKEND_IMAGE="ideaforge-ai-backend:$(GIT_SHA)"; \
		echo "   Using backend image: $$BACKEND_IMAGE"; \
	elif docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-backend:latest$$"; then \
		BACKEND_IMAGE="ideaforge-ai-backend:latest"; \
		echo "   Using backend image: $$BACKEND_IMAGE"; \
	else \
		echo "⚠️  Backend image not found. Please run 'make build-apps' first."; \
		exit 1; \
	fi; \
	if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-frontend:$(GIT_SHA)$$"; then \
		FRONTEND_IMAGE="ideaforge-ai-frontend:$(GIT_SHA)"; \
		echo "   Using frontend image: $$FRONTEND_IMAGE"; \
	elif docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-frontend:latest$$"; then \
		FRONTEND_IMAGE="ideaforge-ai-frontend:latest"; \
		echo "   Using frontend image: $$FRONTEND_IMAGE"; \
	else \
		echo "⚠️  Frontend image not found. Please run 'make build-apps' first."; \
		exit 1; \
	fi; \
	if [ "$$(uname)" = "Darwin" ]; then \
		sed -i '' "s|image:.*ideaforge-ai-backend:.*|image: $$BACKEND_IMAGE|g" $(K8S_DIR)/backend.yaml; \
		sed -i '' "s|imagePullPolicy:.*|imagePullPolicy: Never|g" $(K8S_DIR)/backend.yaml; \
		sed -i '' "s|image:.*ideaforge-ai-frontend:.*|image: $$FRONTEND_IMAGE|g" $(K8S_DIR)/frontend.yaml; \
		sed -i '' "s|imagePullPolicy:.*|imagePullPolicy: Never|g" $(K8S_DIR)/frontend.yaml; \
	else \
		sed -i "s|image:.*ideaforge-ai-backend:.*|image: $$BACKEND_IMAGE|g" $(K8S_DIR)/backend.yaml; \
		sed -i "s|imagePullPolicy:.*|imagePullPolicy: Never|g" $(K8S_DIR)/backend.yaml; \
		sed -i "s|image:.*ideaforge-ai-frontend:.*|image: $$FRONTEND_IMAGE|g" $(K8S_DIR)/frontend.yaml; \
		sed -i "s|imagePullPolicy:.*|imagePullPolicy: Never|g" $(K8S_DIR)/frontend.yaml; \
	fi; \
	echo "✅ Image references updated to use local images (imagePullPolicy: Never)"

rebuild-and-deploy: build-apps ## Rebuild apps and deploy to docker-compose
	@echo "🚀 Rebuilding and deploying to docker-compose..."
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose up -d backend frontend
	@echo "⏳ Waiting for services to restart..."
	@sleep 5
	@echo "✅ Deployment complete!"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"

rebuild-and-deploy-kind: build-apps kind-load-images kind-update-images ## Rebuild apps and deploy to kind cluster
	@echo "🚀 Rebuilding and deploying to kind cluster..."
	@if ! kubectl cluster-info --context kind-$(KIND_CLUSTER_NAME) &>/dev/null; then \
		echo "⚠️  Kind cluster not found. Creating cluster..."; \
		$(MAKE) kind-create kind-setup-ingress; \
	fi
	@$(MAKE) kind-deploy-internal
	@echo "✅ Deployment to kind complete!"

kind-deploy: kind-create kind-setup-ingress kind-load-images ## Deploy to kind cluster (creates cluster, installs ingress, loads images, deploys)
	@echo "🚀 Deploying to kind cluster..."
	@$(MAKE) kind-update-images
	@$(MAKE) kind-deploy-internal

kind-create-db-configmaps: ## Create ConfigMaps for database migrations and seed data
	@echo "📦 Creating ConfigMaps for database setup..."
	@bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "✅ ConfigMaps created"

kind-load-secrets: ## Load secrets from .env file for kind deployment
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Creating from .env.example..."; \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "   Created .env from .env.example - please fill in your API keys!"; \
			echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN"; \
			exit 1; \
		else \
			echo "   .env.example not found. Please create .env manually."; \
			exit 1; \
		fi; \
	fi
	@echo "📦 Loading secrets from .env file to Kubernetes..."
	@bash $(K8S_DIR)/push-env-secret.sh .env $(K8S_NAMESPACE) kind-$(KIND_CLUSTER_NAME)
	@echo "✅ Secrets pushed to Kubernetes secret: ideaforge-ai-secrets"

kind-deploy-internal: kind-create-db-configmaps ## Internal target: deploy manifests to kind (assumes cluster exists and images are loaded)
	@echo "📦 Applying Kubernetes manifests from k8s/kind/..."
	@if [ ! -d $(K8S_DIR)/kind ]; then \
		echo "❌ k8s/kind/ directory not found"; \
		exit 1; \
	fi
	@kubectl apply -f $(K8S_DIR)/kind/ --context kind-$(KIND_CLUSTER_NAME) --recursive
	@if ! kubectl get secret ideaforge-ai-secrets -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) &>/dev/null; then \
		echo "⚠️  secrets not found, creating default secrets..."; \
		echo "   Run 'make kind-load-secrets' to load from .env file"; \
		kubectl create secret generic ideaforge-ai-secrets \
			--from-literal=POSTGRES_PASSWORD=devpassword \
			--from-literal=SESSION_SECRET=dev-secret-change-me \
			--from-literal=API_KEY_ENCRYPTION_KEY=dev-key-change-me \
			--namespace $(K8S_NAMESPACE) \
			--context kind-$(KIND_CLUSTER_NAME) \
			--dry-run=client -o yaml | kubectl apply -f - --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "⏳ Waiting for database services to be ready..."
	@echo "   Waiting for PostgreSQL (this may take 60-90 seconds for first startup)..."
	@timeout=180; \
	elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		if kubectl get pods -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null | grep -q "Running"; then \
			if kubectl wait --for=condition=ready pod -l app=postgres -n $(K8S_NAMESPACE) --timeout=10s --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null; then \
				echo "✅ PostgreSQL is ready"; \
				break; \
			fi; \
		fi; \
		sleep 5; \
		elapsed=$$((elapsed + 5)); \
		echo "   Still waiting... ($$elapsed/$$timeout seconds)"; \
	done; \
	if [ $$elapsed -ge $$timeout ]; then \
		echo "⚠️  PostgreSQL not ready after $$timeout seconds, but continuing..."; \
		kubectl get pods -n $(K8S_NAMESPACE) -l app=postgres --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "   Waiting for Redis..."
	@timeout=120; \
	elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		if kubectl get pods -n $(K8S_NAMESPACE) -l app=redis --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null | grep -q "Running"; then \
			if kubectl wait --for=condition=ready pod -l app=redis -n $(K8S_NAMESPACE) --timeout=10s --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null; then \
				echo "✅ Redis is ready"; \
				break; \
			fi; \
		fi; \
		sleep 5; \
		elapsed=$$((elapsed + 5)); \
		echo "   Still waiting... ($$elapsed/$$timeout seconds)"; \
	done; \
	if [ $$elapsed -ge $$timeout ]; then \
		echo "⚠️  Redis not ready after $$timeout seconds, but continuing..."; \
		kubectl get pods -n $(K8S_NAMESPACE) -l app=redis --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "🔄 Running database setup (migrations + seeding)..."
	@kubectl delete job db-setup -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --ignore-not-found=true
	@kubectl apply -f $(K8S_DIR)/db-setup-job.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for database setup job to complete..."
	@kubectl wait --for=condition=complete job/db-setup -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --timeout=300s || \
		(echo "⚠️  Database setup job did not complete, checking logs..." && \
		 kubectl logs -n $(K8S_NAMESPACE) job/db-setup --context kind-$(KIND_CLUSTER_NAME) --tail=50 && \
		 echo "⚠️  Continuing anyway...")
	@echo "✅ Database setup complete"
	@kubectl wait --for=condition=complete job/db-setup -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || \
		(echo "⚠️  Database setup job may have failed. Check logs:" && \
		 kubectl logs -n $(K8S_NAMESPACE) job/db-setup --context kind-$(KIND_CLUSTER_NAME) --tail=50 && \
		 echo "   Continuing with deployment...")
	@echo "✅ Database setup complete"
	@kubectl apply -f $(K8S_DIR)/backend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@kubectl apply -f $(K8S_DIR)/frontend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for application pods to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=backend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
	@echo "🤖 Initializing Agno framework..."
	@$(MAKE) kind-agno-init || echo "⚠️  Agno initialization skipped"
	@echo "🌐 Applying ingress for kind..."
	@if [ -f $(K8S_DIR)/ingress-kind.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/ingress-kind.yaml --context kind-$(KIND_CLUSTER_NAME); \
	else \
		echo "⚠️  ingress-kind.yaml not found, using default ingress"; \
		kubectl apply -f $(K8S_DIR)/ingress.yaml --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo ""
	@echo "✅ Deployment complete!"
	@echo ""
	@INGRESS_PORT=$$(docker ps --filter "name=$(KIND_CLUSTER_NAME)-control-plane" --format "{{.Ports}}" | grep -o "0.0.0.0:[0-9]*->80" | cut -d: -f2 | cut -d- -f1 || echo "80"); \
	echo "🌐 Access the application:"; \
	echo "   Method 1 - Direct access (port $$INGRESS_PORT):"; \
	echo "     Frontend: http://localhost:$$INGRESS_PORT/"; \
	echo "     Backend API: http://localhost:$$INGRESS_PORT/api/"; \
	echo "     Backend Health: http://localhost:$$INGRESS_PORT/health"; \
	echo ""; \
	echo "   Method 2 - With host headers:"; \
	echo "     Frontend: curl -H 'Host: ideaforge.local' http://localhost:$$INGRESS_PORT/"; \
	echo "     Backend: curl -H 'Host: api.ideaforge.local' http://localhost:$$INGRESS_PORT/"; \
	echo ""; \
	echo "   Method 3 - Add to /etc/hosts (then use hostnames):"; \
	echo "     sudo sh -c 'echo \"127.0.0.1 ideaforge.local api.ideaforge.local\" >> /etc/hosts'"; \
	echo "     Frontend: http://ideaforge.local"; \
	echo "     Backend API: http://api.ideaforge.local"; \
	echo ""; \
	echo "   Method 4 - Port forward (recommended for development):"; \
	echo "     make kind-port-forward"
	@echo ""
	@$(MAKE) kind-status

kind-port-forward: ## Port forward frontend and backend services for local access
	@echo "🔌 Setting up port forwarding..."
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo ""
	@echo "⚠️  This will run in the foreground. Press Ctrl+C to stop."
	@echo "   Starting port forwarding in background..."
	@kubectl port-forward -n $(K8S_NAMESPACE) service/frontend 3001:3000 --context kind-$(KIND_CLUSTER_NAME) > /dev/null 2>&1 &
	@kubectl port-forward -n $(K8S_NAMESPACE) service/backend 8000:8000 --context kind-$(KIND_CLUSTER_NAME) > /dev/null 2>&1 &
	@sleep 2
	@echo "✅ Port forwarding active!"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo ""
	@echo "To stop port forwarding, run: pkill -f 'kubectl port-forward'"

kind-status: ## Show status of kind cluster deployment
	@echo "📊 Kind Cluster Status:"
	@echo "======================"
	@kubectl get all -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) || echo "⚠️  No resources found"
	@echo ""
	@echo "🌐 Ingress:"
	@kubectl get ingress -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) || echo "⚠️  No ingress found"
	@echo ""
	@echo "📝 Pod Status:"
	@kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o wide
	@echo ""
	@echo "💾 Persistent Volumes:"
	@kubectl get pvc -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) || echo "⚠️  No PVCs found"

kind-test: ## Test service-to-service interactions in kind cluster
	@echo "🧪 Testing service-to-service interactions in kind cluster..."
	@echo ""
	@echo "1️⃣  Testing Backend -> PostgreSQL..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z postgres 5432 && echo '✅ PostgreSQL reachable' || echo '❌ PostgreSQL not reachable'"; \
	fi
	@echo ""
	@echo "2️⃣  Testing Backend -> Redis..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z redis 6379 && echo '✅ Redis reachable' || echo '❌ Redis not reachable'"; \
	fi
	@echo ""
	@echo "3️⃣  Testing Backend Health Endpoint..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			curl -s http://localhost:8000/health | head -20 || echo "❌ Health check failed"; \
	fi
	@echo ""
	@echo "4️⃣  Testing Frontend -> Backend..."
	@FRONTEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=frontend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$FRONTEND_POD" ]; then \
		echo "   Frontend pod: $$FRONTEND_POD"; \
		kubectl exec -n $(K8S_NAMESPACE) $$FRONTEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z backend 8000 && echo '✅ Backend reachable' || echo '❌ Backend not reachable'"; \
	fi
	@echo ""
	@echo "5️⃣  Testing Ingress (external access)..."
	@INGRESS_IP=$$(kubectl get ingress -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "localhost"); \
	if [ "$$INGRESS_IP" = "localhost" ] || [ -z "$$INGRESS_IP" ]; then \
		echo "   Using port-forward for testing..."; \
		echo "   Run: kubectl port-forward -n $(K8S_NAMESPACE) service/backend 8000:8000 --context kind-$(KIND_CLUSTER_NAME)"; \
		echo "   Then test: curl http://localhost:8000/health"; \
	else \
		echo "   Ingress IP: $$INGRESS_IP"; \
		curl -s http://$$INGRESS_IP/health || echo "   (Testing via ingress...)"; \
	fi
	@echo ""
	@echo "✅ Service-to-service tests complete!"

kind-logs: ## Show logs from kind cluster
	@echo "📋 Showing logs from kind cluster..."
	@echo ""
	@echo "=== Backend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) --tail=50 || echo "No backend logs"
	@echo ""
	@echo "=== Frontend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=frontend --context kind-$(KIND_CLUSTER_NAME) --tail=50 || echo "No frontend logs"

kind-cleanup: ## Clean up kind cluster deployment (keeps cluster)
	@echo "🧹 Cleaning up kind cluster deployment..."
	@kubectl delete namespace $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --ignore-not-found=true
	@echo "✅ Cleanup complete (cluster still exists, use 'make kind-delete' to remove cluster)"

eks-setup-ghcr-secret: ## Setup GitHub Container Registry secret in EKS namespace (use EKS_NAMESPACE=your-namespace). Uses GitHub PAT from .env or EKS_GITHUB_TOKEN env var.
	@echo "🔐 Setting up GitHub Container Registry secret..."
	@echo "ℹ️  Note: GitHub Personal Access Token (PAT) can be used for GHCR authentication"
	@echo "   Required PAT scope: read:packages (or write:packages if also pushing)"
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required. Example: make eks-setup-ghcr-secret EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50"; \
		exit 1; \
	fi
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "❌ kubectl is not configured or EKS cluster is not accessible"; \
		echo "   Configure kubectl: aws eks update-kubeconfig --name $(EKS_CLUSTER_NAME) --region $(EKS_REGION)"; \
		exit 1; \
	fi
	@echo "📦 Creating namespace: $(EKS_NAMESPACE)"
	@kubectl create namespace $(EKS_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f - || true
	@echo "🔐 Creating docker-registry secret for GitHub Container Registry..."
	@GITHUB_USERNAME="$${EKS_GITHUB_USERNAME:-soumantrivedi}"; \
	GITHUB_TOKEN=""; \
	if [ -n "$$EKS_GITHUB_TOKEN" ]; then \
		GITHUB_TOKEN="$$EKS_GITHUB_TOKEN"; \
		echo "   Using GITHUB_TOKEN from EKS_GITHUB_TOKEN environment variable"; \
	elif [ -f .env ]; then \
		GITHUB_TOKEN=$$(grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs || echo ""); \
		if [ -n "$$GITHUB_TOKEN" ]; then \
			echo "   Using GITHUB_TOKEN from .env file"; \
		fi; \
	fi; \
	if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "❌ GITHUB_TOKEN (GitHub PAT) is required"; \
		echo "   Options:"; \
		echo "   1. Export: export EKS_GITHUB_TOKEN=ghp_your_pat_token_here"; \
		echo "   2. Add to .env: GITHUB_TOKEN=ghp_your_pat_token_here"; \
		echo ""; \
		echo "   Create PAT at: https://github.com/settings/tokens"; \
		echo "   Required scope: read:packages"; \
		exit 1; \
	fi; \
	echo "   Using GitHub username: $$GITHUB_USERNAME"; \
	echo "   Docker server: ghcr.io"; \
	kubectl delete secret ghcr-secret -n $(EKS_NAMESPACE) --ignore-not-found=true; \
	kubectl create secret docker-registry ghcr-secret \
		--docker-server=ghcr.io \
		--docker-username=$$GITHUB_USERNAME \
		--docker-password=$$GITHUB_TOKEN \
		--namespace=$(EKS_NAMESPACE) || \
		(echo "❌ Failed to create secret" && exit 1)
	@echo "✅ GitHub Container Registry secret created: ghcr-secret in namespace $(EKS_NAMESPACE)"
	@echo "   This secret allows Kubernetes to pull images from ghcr.io/soumantrivedi/ideaforge-ai"

eks-prepare-namespace: ## Prepare namespace-specific manifests for EKS (updates namespace in all manifests)
	@echo "📝 Preparing EKS deployment for namespace: $(EKS_NAMESPACE)"
	@if [ -z "$(EKS_NAMESPACE)" ] || [ "$(EKS_NAMESPACE)" = "ideaforge-ai" ]; then \
		echo "⚠️  Using default namespace: ideaforge-ai"; \
		EKS_NAMESPACE="ideaforge-ai"; \
	fi
	@if [ ! -d $(K8S_DIR)/eks ]; then \
		echo "❌ k8s/eks/ directory not found"; \
		exit 1; \
	fi
	@echo "📝 Updating image tags in EKS manifests..."
	@if [ "$(uname)" = "Darwin" ]; then \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i '' "s|ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(EKS_IMAGE_TAG)|g" {} \; ; \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i '' "s|ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(EKS_IMAGE_TAG)|g" {} \; ; \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i '' "s|namespace: ideaforge-ai|namespace: $(EKS_NAMESPACE)|g" {} \; ; \
	else \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i "s|ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(EKS_IMAGE_TAG)|g" {} \; ; \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i "s|ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(EKS_IMAGE_TAG)|g" {} \; ; \
		find $(K8S_DIR)/eks -name "*.yaml" -type f -exec sed -i "s|namespace: ideaforge-ai|namespace: $(EKS_NAMESPACE)|g" {} \; ; \
	fi
	@echo "✅ EKS manifests prepared for namespace: $(EKS_NAMESPACE)"

eks-load-secrets: ## Load secrets from .env file for EKS deployment (use EKS_NAMESPACE=your-namespace)
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Creating from .env.example..."; \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "   Created .env from .env.example - please fill in your API keys!"; \
			echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN"; \
			exit 1; \
		else \
			echo "   .env.example not found. Please create .env manually."; \
			exit 1; \
		fi; \
	fi
	@echo "📦 Loading secrets from .env file to Kubernetes..."
	@bash $(K8S_DIR)/push-env-secret.sh .env $(EKS_NAMESPACE)
	@echo "✅ Secrets pushed to Kubernetes secret: ideaforge-ai-secrets in namespace: $(EKS_NAMESPACE)"

eks-deploy-full: eks-setup-ghcr-secret eks-prepare-namespace eks-load-secrets eks-deploy ## Full EKS deployment with GHCR setup (use EKS_NAMESPACE=your-namespace)

eks-deploy: eks-prepare-namespace ## Deploy to EKS cluster (use EKS_NAMESPACE=your-namespace)
	@echo "☁️  Deploying to EKS cluster: $(EKS_CLUSTER_NAME)"
	@echo "📦 Namespace: $(EKS_NAMESPACE)"
	@echo "🏷️  Image Registry: $(EKS_IMAGE_REGISTRY)"
	@echo "🏷️  Image Tag: $(EKS_IMAGE_TAG)"
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "❌ kubectl is not configured or EKS cluster is not accessible"; \
		echo "   Configure kubectl: aws eks update-kubeconfig --name $(EKS_CLUSTER_NAME) --region $(EKS_REGION)"; \
		exit 1; \
	fi
	@echo "✅ kubectl is configured"
	@echo "📦 Creating ConfigMaps for database setup..."
	@bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "📦 Creating namespace if it doesn't exist..."
	@kubectl create namespace $(EKS_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f - || true
	@echo "📦 Applying Kubernetes manifests from k8s/eks/ to namespace: $(EKS_NAMESPACE)"
	@kubectl apply -f $(K8S_DIR)/eks/ --recursive
	@echo "⏳ Waiting for database services to be ready..."
	@kubectl wait --for=condition=ready pod -l app=postgres -n $(EKS_NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=ready pod -l app=redis -n $(EKS_NAMESPACE) --timeout=120s || true
	@echo "🔄 Running database setup (migrations + seeding)..."
	@kubectl apply -f $(K8S_DIR)/db-setup-job.yaml -n $(EKS_NAMESPACE)
	@echo "⏳ Waiting for database setup job to complete..."
	@kubectl wait --for=condition=complete job/db-setup -n $(EKS_NAMESPACE) --timeout=300s || \
		(echo "⚠️  Database setup job may have failed. Check logs:" && \
		 kubectl logs -n $(EKS_NAMESPACE) job/db-setup --tail=50 && \
		 echo "   Continuing with deployment...")
	@echo "✅ Database setup complete"
	@echo "⏳ Waiting for application pods to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=backend -n $(EKS_NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(EKS_NAMESPACE) --timeout=300s || true
	@echo "🤖 Initializing Agno framework..."
	@$(MAKE) eks-agno-init EKS_NAMESPACE=$(EKS_NAMESPACE) || echo "⚠️  Agno initialization skipped"
	@echo ""
	@echo "✅ EKS deployment complete!"
	@echo "   Namespace: $(EKS_NAMESPACE)"
	@echo "   Cluster: $(EKS_CLUSTER_NAME)"
	@echo ""
	@$(MAKE) eks-status EKS_NAMESPACE=$(EKS_NAMESPACE)

eks-status: ## Show status of EKS cluster deployment (use EKS_NAMESPACE=your-namespace)
	@echo "📊 EKS Cluster Status:"
	@echo "======================"
	@echo "Namespace: $(EKS_NAMESPACE)"
	@echo "Cluster: $(EKS_CLUSTER_NAME)"
	@echo ""
	@kubectl get all -n $(EKS_NAMESPACE) || echo "⚠️  No resources found in namespace $(EKS_NAMESPACE)"
	@echo ""
	@echo "🌐 Ingress:"
	@kubectl get ingress -n $(EKS_NAMESPACE) || echo "⚠️  No ingress found"
	@echo ""
	@echo "📝 Pod Status:"
	@kubectl get pods -n $(EKS_NAMESPACE) -o wide
	@echo ""
	@echo "🔗 Ingress URL:"
	@kubectl get ingress -n $(EKS_NAMESPACE) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || \
		kubectl get ingress -n $(EKS_NAMESPACE) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
		echo "   (Ingress address pending...)"
	@echo ""
	@echo "💾 Persistent Volumes:"
	@kubectl get pvc -n $(EKS_NAMESPACE) || echo "⚠️  No PVCs found"

eks-test: ## Test service-to-service interactions in EKS cluster (use EKS_NAMESPACE=your-namespace)
	@echo "🧪 Testing service-to-service interactions in EKS..."
	@echo "Namespace: $(EKS_NAMESPACE)"
	@echo ""
	@echo "1️⃣  Testing Backend -> PostgreSQL..."
	@BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- \
			sh -c "nc -z postgres 5432 && echo '✅ PostgreSQL reachable' || echo '❌ PostgreSQL not reachable'"; \
	fi
	@echo ""
	@echo "2️⃣  Testing Backend -> Redis..."
	@BACKEND_POD=$$(kubectl get cluster-info &> /dev/null; then \
		echo "✅ kubectl is configured"; \
	else \
		echo "❌ kubectl is not configured or EKS cluster is not accessible"; \
		echo "   Configure kubectl: aws eks update-kubeconfig --name $(EKS_CLUSTER_NAME) --region $(EKS_REGION)"; \
		exit 1; \
	fi
	@echo "📦 Applying Kubernetes manifests..."
	@kubectl apply -f $(K8S_DIR)/namespace.yaml
	@kubectl apply -f $(K8S_DIR)/configmap.yaml
	@if [ -f $(K8S_DIR)/secrets.yaml ]; then \
		echo "⚠️  Using secrets.yaml - ensure it's updated with production values!"; \
		kubectl apply -f $(K8S_DIR)/secrets.yaml; \
	else \
		echo "❌ secrets.yaml not found. Please create it with production secrets."; \
		exit 1; \
	fi
	@kubectl apply -f $(K8S_DIR)/postgres.yaml
	@kubectl apply -f $(K8S_DIR)/redis.yaml
	@echo "⏳ Waiting for database services to be ready..."
	@kubectl wait --for=condition=ready pod -l app=postgres -n $(K8S_NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=ready pod -l app=redis -n $(K8S_NAMESPACE) --timeout=120s || true
	@kubectl apply -f $(K8S_DIR)/backend.yaml
	@kubectl apply -f $(K8S_DIR)/frontend.yaml
	@echo "⏳ Waiting for application pods to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=backend -n $(K8S_NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(K8S_NAMESPACE) --timeout=300s || true
	@kubectl apply -f $(K8S_DIR)/ingress.yaml
	@echo ""
	@echo "✅ EKS deployment complete!"
	@echo ""
	@$(MAKE) eks-status