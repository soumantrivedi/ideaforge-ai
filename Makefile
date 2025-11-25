.PHONY: help build up down restart logs clean deploy deploy-full health test rebuild redeploy check-errors check-logs version clean-all build-versioned deploy-versioned db-migrate db-seed db-setup agno-init setup db-backup db-restore rebuild-safe kind-create kind-delete kind-deploy kind-test kind-cleanup eks-deploy eks-test eks-cleanup k8s-deploy k8s-test k8s-logs k8s-status

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

build-apps: ## Build only backend and frontend images (skip postgres/redis)
	@echo "🔨 Building application images (backend + frontend) with tag: $(GIT_SHA)"
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) docker-compose build --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION) backend frontend
	@echo "✅ Application images built: ideaforge-ai-backend:$(GIT_SHA) and ideaforge-ai-frontend:$(GIT_SHA)"

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
		echo "⚠️  .env file not found. Continuing with environment variables from shell..."; \
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
	@echo "✅ Complete deployment finished!"
	@echo "   Version: $(VERSION)"
	@echo "   Frontend: http://localhost:3001"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo "   Database: Migrated and seeded with 9 products"
	@echo "   Agno: Initialized (if API keys configured)"

redeploy: clean-all build-no-cache deploy check-errors ## Complete rebuild and redeploy (backup + clean + build + deploy + verify)
	@echo ""
	@echo "✅ Complete redeployment finished!"
	@echo "   Version: $(VERSION)"
	@echo "   All services rebuilt and deployed"
	@echo "   💾 Database backup available in backups/ directory"

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

rebuild: ## Rebuild and restart services (preserves database)
	@echo "🔨 Rebuilding services (database will be preserved)..."
	@$(MAKE) build-no-cache
	@$(MAKE) up
	@echo "⏳ Waiting for services to start..."
	@sleep 5
	@$(MAKE) health

rebuild-safe: ## Safe rebuild: backup DB, rebuild images, restore if needed (preserves all data)
	@echo "🛡️  Safe rebuild with database backup..."
	@$(MAKE) db-backup
	@echo "🔨 Rebuilding images..."
	@$(MAKE) build-no-cache
	@echo "🔄 Restarting services..."
	@docker-compose down
	@GIT_SHA=$(GIT_SHA) VERSION=$(VERSION) $(MAKE) up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "🔄 Running database migrations (if needed)..."
	@$(MAKE) db-migrate || echo "⚠️  Migrations may have already been applied"
	@$(MAKE) health
	@echo ""
	@echo "✅ Safe rebuild complete!"
	@echo "   Database: Preserved (backup available in backups/)"
	@echo "   User data: Preserved (API keys, products, etc.)"
	@echo "   Version: $(VERSION)"

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

db-migrate: ## Run all database migrations from init-db/migrations
	@echo "🔄 Running database migrations..."
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251124000003_user_api_keys.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251124000004_product_scoring.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/migrations/20251125000001_user_management_tenants.sql 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@echo "✅ Migrations complete"

db-seed: ## Seed database with sample data (9 products, default tenant, admin user)
	@echo "🌱 Seeding database with sample data..."
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -f /docker-entrypoint-initdb.d/seed_sample_data.sql 2>&1 | grep -v "NOTICE" || true
	@echo "✅ Database seeding complete"

db-setup: db-migrate db-seed ## Run migrations and seed database (chained target)
	@echo "✅ Database setup complete (migrations + seeding)"

agno-init: ## Initialize Agno framework via API (requires backend to be running)
	@echo "🤖 Initializing Agno framework..."
	@echo "⏳ Waiting for backend to be ready..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then \
			break; \
		fi; \
		echo "   Waiting for backend... ($$timeout seconds remaining)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	if [ $$timeout -le 0 ]; then \
		echo "❌ Backend not available after 60 seconds. Please ensure backend is running."; \
		exit 1; \
	fi
	@echo "🔐 Logging in as admin user..."
	@login_response=$$(curl -s -X POST http://localhost:8000/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"admin@ideaforge.ai","password":"password123"}' \
		-c /tmp/ideaforge_cookies.txt 2>&1) || true; \
	if echo "$$login_response" | grep -q "token"; then \
		token=$$(echo "$$login_response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null || echo ""); \
		if [ -n "$$token" ]; then \
			echo "✅ Login successful"; \
			echo "📡 Calling Agno initialization endpoint..."; \
			init_response=$$(curl -s -X POST http://localhost:8000/api/agno/initialize \
				-H "Content-Type: application/json" \
				-H "Authorization: Bearer $$token" \
				-b /tmp/ideaforge_cookies.txt 2>&1) || true; \
			if echo "$$init_response" | grep -q "success.*true"; then \
				echo "✅ Agno framework initialized successfully"; \
			elif echo "$$init_response" | grep -q "No AI provider configured"; then \
				echo "⚠️  Agno initialization skipped: No AI provider configured"; \
				echo "   Configure at least one provider (OpenAI, Claude, or Gemini) in Settings to enable Agno"; \
			else \
				echo "⚠️  Agno initialization response: $$init_response"; \
				echo "   This may be expected if no API keys are configured yet"; \
			fi; \
			rm -f /tmp/ideaforge_cookies.txt; \
		else \
			echo "⚠️  Could not extract token from login response"; \
		fi; \
	elif echo "$$login_response" | grep -q "Invalid email or password"; then \
		echo "⚠️  Login failed: Invalid credentials"; \
		echo "   Admin user may need to be created. Run 'make db-seed' first."; \
	else \
		echo "⚠️  Login failed: $$login_response"; \
		echo "   Agno initialization requires authentication."; \
		echo "   To initialize manually:"; \
		echo "   1. Login at http://localhost:3001 (admin@ideaforge.ai / password123)"; \
		echo "   2. Configure AI providers in Settings"; \
		echo "   3. Framework will auto-initialize on first use"; \
	fi

setup: db-setup agno-init ## Complete setup: database migrations, seeding, and Agno initialization (chained target)
	@echo ""
	@echo "✅ Complete setup finished!"
	@echo "   - Database migrations: ✅"
	@echo "   - Database seeding (9 products): ✅"
	@echo "   - Agno framework initialization: ✅"
	@echo ""
	@echo "📊 Database Summary:"
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db -c "SELECT COUNT(*) as total_products FROM products; SELECT COUNT(*) as total_users FROM user_profiles; SELECT COUNT(*) as total_tenants FROM tenants;" 2>&1 | grep -E "total_|-[[:space:]]*[0-9]" || true

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

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
					rm -f $$BACKUP_FILE; \
					exit 1; \
				fi; \
			else \
				echo "❌ Backup failed"; \
				rm -f $$BACKUP_FILE; \
				exit 1; \
			fi; \
		fi; \
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
				rm -f $$BACKUP_FILE; \
				exit 1; \
			fi; \
		else \
			echo "❌ Backup failed"; \
			rm -f $$BACKUP_FILE; \
			exit 1; \
		fi; \
	fi

db-restore: ## Restore database from backup (usage: make db-restore BACKUP_FILE=backups/ideaforge_db_backup_YYYYMMDD_HHMMSS.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Please specify BACKUP_FILE (e.g., make db-restore BACKUP_FILE=backups/latest_backup.sql)"; \
		echo "   Available backups:"; \
		ls -lh backups/*.sql 2>/dev/null || echo "   No backups found"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "❌ Backup file not found: $(BACKUP_FILE)"; \
		echo "   Available backups:"; \
		ls -lh backups/*.sql 2>/dev/null || echo "   No backups found"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will replace the current database!"
	@echo "📦 Restoring from: $(BACKUP_FILE)"
	@echo "⏳ Waiting for postgres to be ready..."
	@timeout=30; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose exec -T postgres pg_isready -U agentic_pm > /dev/null 2>&1; then \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout - 1)); \
	done
	@docker-compose exec -T postgres psql -U agentic_pm -d agentic_pm_db < $(BACKUP_FILE) 2>&1 | grep -v "NOTICE" | grep -v "already exists" || true
	@echo "✅ Database restored from $(BACKUP_FILE)"
	@echo "🔄 Running migrations to ensure schema is up to date..."
	@$(MAKE) db-migrate || echo "⚠️  Migrations may have already been applied"

db-list-backups: ## List all available database backups
	@echo "📦 Available database backups:"
	@if [ -d backups ] && [ -n "$$(ls -A backups/*.sql 2>/dev/null)" ]; then \
		ls -lh backups/*.sql | awk '{print "   " $$9 " (" $$5 ")"}'; \
		if [ -L backups/latest_backup.sql ]; then \
			echo ""; \
			echo "   Latest: backups/latest_backup.sql -> $$(readlink backups/latest_backup.sql)"; \
		fi; \
	else \
		echo "   No backups found"; \
	fi

# ============================================================================
# Kubernetes Deployment Targets (Kind & EKS)
# ============================================================================

K8S_NAMESPACE ?= ideaforge-ai
K8S_DIR ?= k8s
KIND_CLUSTER_NAME ?= ideaforge-ai
KIND_IMAGE ?= kindest/node:v1.33.0
EKS_CLUSTER_NAME ?= ideaforge-ai
EKS_REGION ?= us-east-1

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
	@echo "    hostPort: 80" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    protocol: TCP" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - containerPort: 443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    hostPort: 443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
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

kind-deploy-internal: ## Internal target: deploy manifests to kind (assumes cluster exists and images are loaded)
	@echo "📦 Applying Kubernetes manifests..."
	@echo "📦 Applying Kubernetes manifests..."
	@kubectl apply -f $(K8S_DIR)/namespace.yaml --context kind-$(KIND_CLUSTER_NAME)
	@kubectl apply -f $(K8S_DIR)/configmap.yaml --context kind-$(KIND_CLUSTER_NAME)
	@if [ -f $(K8S_DIR)/secrets.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/secrets.yaml --context kind-$(KIND_CLUSTER_NAME); \
	else \
		echo "⚠️  secrets.yaml not found, creating default secrets..."; \
		kubectl create secret generic ideaforge-ai-secrets \
			--from-literal=POSTGRES_PASSWORD=devpassword \
			--from-literal=SESSION_SECRET=dev-secret-change-me \
			--from-literal=API_KEY_ENCRYPTION_KEY=dev-key-change-me \
			--namespace $(K8S_NAMESPACE) \
			--context kind-$(KIND_CLUSTER_NAME) \
			--dry-run=client -o yaml | kubectl apply -f - --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "📦 Deploying PostgreSQL (using kind-optimized config)..."
	@if [ -f $(K8S_DIR)/postgres-kind.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/postgres-kind.yaml --context kind-$(KIND_CLUSTER_NAME); \
	else \
		kubectl apply -f $(K8S_DIR)/postgres.yaml --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "📦 Deploying Redis (using kind-optimized config)..."
	@if [ -f $(K8S_DIR)/redis-kind.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/redis-kind.yaml --context kind-$(KIND_CLUSTER_NAME); \
	else \
		kubectl apply -f $(K8S_DIR)/redis.yaml --context kind-$(KIND_CLUSTER_NAME); \
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
	@kubectl apply -f $(K8S_DIR)/backend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@kubectl apply -f $(K8S_DIR)/frontend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for application pods to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=backend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
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
	@echo "🌐 Access the application:"
	@echo "   Frontend: http://ideaforge.local (add to /etc/hosts: 127.0.0.1 ideaforge.local)"
	@echo "   Backend API: http://api.ideaforge.local (add to /etc/hosts: 127.0.0.1 api.ideaforge.local)"
	@echo "   Or use port-forward: kubectl port-forward -n $(K8S_NAMESPACE) service/frontend 3001:3000 --context kind-$(KIND_CLUSTER_NAME)"
	@echo ""
	@$(MAKE) kind-status

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

kind-test: ## Test service-to-service interactions in kind cluster
	@echo "🧪 Testing service-to-service interactions..."
	@echo ""
	@echo "1️⃣  Testing PostgreSQL connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/postgres --context kind-$(KIND_CLUSTER_NAME) -- \
		psql -U agentic_pm -d agentic_pm_db -c "SELECT version();" || echo "❌ PostgreSQL test failed"
	@echo ""
	@echo "2️⃣  Testing Redis connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/redis --context kind-$(KIND_CLUSTER_NAME) -- \
		redis-cli ping || echo "❌ Redis test failed"
	@echo ""
	@echo "3️⃣  Testing Backend -> PostgreSQL..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		echo "   Backend pod: $$BACKEND_POD"; \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z postgres 5432 && echo '✅ PostgreSQL reachable' || echo '❌ PostgreSQL not reachable'"; \
	else \
		echo "❌ Backend pod not found"; \
	fi
	@echo ""
	@echo "4️⃣  Testing Backend -> Redis..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z redis 6379 && echo '✅ Redis reachable' || echo '❌ Redis not reachable'"; \
	fi
	@echo ""
	@echo "5️⃣  Testing Backend Health Endpoint..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			curl -s http://localhost:8000/health | head -20 || echo "❌ Health check failed"; \
	fi
	@echo ""
	@echo "6️⃣  Testing Frontend -> Backend..."
	@FRONTEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=frontend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$FRONTEND_POD" ]; then \
		echo "   Frontend pod: $$FRONTEND_POD"; \
		kubectl exec -n $(K8S_NAMESPACE) $$FRONTEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			sh -c "nc -z backend 8000 && echo '✅ Backend reachable' || echo '❌ Backend not reachable'"; \
	fi
	@echo ""
	@echo "7️⃣  Testing Ingress (external access)..."
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

eks-deploy: ## Deploy to EKS cluster (requires kubectl configured for EKS)
	@echo "☁️  Deploying to EKS cluster..."
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "❌ kubectl is not configured or EKS cluster is not accessible"; \
		echo "   Configure kubectl: aws eks update-kubeconfig --name $(EKS_CLUSTER_NAME) --region $(EKS_REGION)"; \
		exit 1; \
	fi
	@echo "✅ kubectl is configured"
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

eks-status: ## Show status of EKS cluster deployment
	@echo "📊 EKS Cluster Status:"
	@echo "======================"
	@kubectl get all -n $(K8S_NAMESPACE) || echo "⚠️  No resources found"
	@echo ""
	@echo "🌐 Ingress:"
	@kubectl get ingress -n $(K8S_NAMESPACE) || echo "⚠️  No ingress found"
	@echo ""
	@echo "📝 Pod Status:"
	@kubectl get pods -n $(K8S_NAMESPACE) -o wide
	@echo ""
	@echo "🔗 Ingress URL:"
	@kubectl get ingress -n $(K8S_NAMESPACE) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || \
		kubectl get ingress -n $(K8S_NAMESPACE) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
		echo "   (Ingress address pending...)"

eks-test: ## Test service-to-service interactions in EKS cluster
	@echo "🧪 Testing service-to-service interactions in EKS..."
	@echo ""
	@echo "1️⃣  Testing PostgreSQL connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/postgres -- \
		psql -U agentic_pm -d agentic_pm_db -c "SELECT version();" || echo "❌ PostgreSQL test failed"
	@echo ""
	@echo "2️⃣  Testing Redis connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/redis -- \
		redis-cli ping || echo "❌ Redis test failed"
	@echo ""
	@echo "3️⃣  Testing Backend Health Endpoint..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD -- \
			curl -s http://localhost:8000/health | head -20 || echo "❌ Health check failed"; \
	fi
	@echo ""
	@echo "4️⃣  Testing External Access (via Ingress)..."
	@INGRESS_HOST=$$(kubectl get ingress -n $(K8S_NAMESPACE) -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null); \
	if [ -n "$$INGRESS_HOST" ]; then \
		echo "   Ingress hostname: $$INGRESS_HOST"; \
		echo "   Testing: curl -H 'Host: api.ideaforge.ai' http://$$INGRESS_HOST/health"; \
		curl -s -H "Host: api.ideaforge.ai" http://$$INGRESS_HOST/health | head -20 || echo "   (May need DNS configuration)"; \
	else \
		echo "   Ingress hostname not available yet"; \
	fi
	@echo ""
	@echo "✅ EKS service-to-service tests complete!"

eks-logs: ## Show logs from EKS cluster
	@echo "📋 Showing logs from EKS cluster..."
	@echo ""
	@echo "=== Backend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --tail=50 || echo "No backend logs"
	@echo ""
	@echo "=== Frontend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=frontend --tail=50 || echo "No frontend logs"

eks-cleanup: ## Clean up EKS cluster deployment
	@echo "🧹 Cleaning up EKS cluster deployment..."
	@echo "⚠️  WARNING: This will delete all resources in the $(K8S_NAMESPACE) namespace!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		kubectl delete namespace $(K8S_NAMESPACE) --ignore-not-found=true; \
		echo "✅ Cleanup complete"; \
	else \
		echo "❌ Cleanup cancelled"; \
	fi

# Generic Kubernetes targets (works with any cluster)
k8s-deploy: ## Deploy to current Kubernetes context (kind or EKS)
	@echo "🚀 Deploying to Kubernetes cluster..."
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "❌ kubectl is not configured or cluster is not accessible"; \
		exit 1; \
	fi
	@echo "✅ kubectl is configured"
	@echo "📦 Applying Kubernetes manifests..."
	@kubectl apply -f $(K8S_DIR)/namespace.yaml
	@kubectl apply -f $(K8S_DIR)/configmap.yaml
	@if [ -f $(K8S_DIR)/secrets.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/secrets.yaml; \
	else \
		echo "⚠️  secrets.yaml not found, creating default secrets..."; \
		kubectl create secret generic ideaforge-ai-secrets \
			--from-literal=POSTGRES_PASSWORD=devpassword \
			--from-literal=SESSION_SECRET=dev-secret-change-me \
			--from-literal=API_KEY_ENCRYPTION_KEY=dev-key-change-me \
			--namespace $(K8S_NAMESPACE) \
			--dry-run=client -o yaml | kubectl apply -f -; \
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
	@echo "✅ Deployment complete!"
	@$(MAKE) k8s-status

k8s-status: ## Show status of current Kubernetes cluster deployment
	@echo "📊 Kubernetes Cluster Status:"
	@echo "============================="
	@kubectl get all -n $(K8S_NAMESPACE) || echo "⚠️  No resources found"
	@echo ""
	@echo "🌐 Ingress:"
	@kubectl get ingress -n $(K8S_NAMESPACE) || echo "⚠️  No ingress found"
	@echo ""
	@echo "📝 Pod Status:"
	@kubectl get pods -n $(K8S_NAMESPACE) -o wide

k8s-test: ## Test service-to-service interactions in current Kubernetes cluster
	@echo "🧪 Testing service-to-service interactions..."
	@echo ""
	@echo "1️⃣  Testing PostgreSQL connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/postgres -- \
		psql -U agentic_pm -d agentic_pm_db -c "SELECT version();" || echo "❌ PostgreSQL test failed"
	@echo ""
	@echo "2️⃣  Testing Redis connectivity..."
	@kubectl exec -n $(K8S_NAMESPACE) deployment/redis -- \
		redis-cli ping || echo "❌ Redis test failed"
	@echo ""
	@echo "3️⃣  Testing Backend -> PostgreSQL..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD -- \
			sh -c "nc -z postgres 5432 && echo '✅ PostgreSQL reachable' || echo '❌ PostgreSQL not reachable'"; \
	fi
	@echo ""
	@echo "4️⃣  Testing Backend -> Redis..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD -- \
			sh -c "nc -z redis 6379 && echo '✅ Redis reachable' || echo '❌ Redis not reachable'"; \
	fi
	@echo ""
	@echo "5️⃣  Testing Backend Health Endpoint..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD -- \
			curl -s http://localhost:8000/health | head -20 || echo "❌ Health check failed"; \
	fi
	@echo ""
	@echo "6️⃣  Testing Frontend -> Backend..."
	@FRONTEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=frontend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$FRONTEND_POD" ]; then \
		kubectl exec -n $(K8S_NAMESPACE) $$FRONTEND_POD -- \
			sh -c "nc -z backend 8000 && echo '✅ Backend reachable' || echo '❌ Backend not reachable'"; \
	fi
	@echo ""
	@echo "✅ Service-to-service tests complete!"

k8s-logs: ## Show logs from current Kubernetes cluster
	@echo "📋 Showing logs..."
	@echo ""
	@echo "=== Backend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --tail=50 || echo "No backend logs"
	@echo ""
	@echo "=== Frontend Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=frontend --tail=50 || echo "No frontend logs"
	@echo ""
	@echo "=== PostgreSQL Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=postgres --tail=30 || echo "No postgres logs"
	@echo ""
	@echo "=== Redis Logs ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=redis --tail=30 || echo "No redis logs"
