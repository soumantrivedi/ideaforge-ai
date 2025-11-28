.PHONY: help build-apps build-no-cache version kind-create kind-delete kind-deploy kind-test kind-cleanup eks-deploy eks-test kind-agno-init eks-agno-init kind-load-secrets eks-load-secrets eks-setup-ghcr-secret eks-prepare-namespace

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
	@echo "Local Development (Kind Cluster):"
	@grep -E '^kind-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Production (EKS Cluster):"
	@grep -E '^eks-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Build & Utilities:"
	@grep -E '^(build|version|help):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Base Image:"
	@grep -E '^build-backend-base.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

version: ## Show current version information
	@echo "Git SHA: $(GIT_SHA)"
	@echo "Version: $(VERSION)"
	@echo "Image Tag: $(IMAGE_TAG)"

build-backend-base: ## Build backend base image (contains system dependencies and Python packages)
	@echo "🔨 Building backend base image..."
	@docker build -f Dockerfile.base.backend -t ideaforge-ai-backend-base:latest .
	@echo "✅ Backend base image built: ideaforge-ai-backend-base:latest"

build-backend-base-push: build-backend-base ## Build and push backend base image to GHCR
	@echo "📤 Pushing backend base image to GHCR..."
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "⚠️  GITHUB_TOKEN not set. Skipping push."; \
		echo "   To push, set GITHUB_TOKEN environment variable"; \
		exit 0; \
	fi
	@echo $$GITHUB_TOKEN | docker login ghcr.io -u soumantrivedi --password-stdin
	@docker tag ideaforge-ai-backend-base:latest ghcr.io/soumantrivedi/ideaforge-ai/backend-base:latest
	@docker push ghcr.io/soumantrivedi/ideaforge-ai/backend-base:latest
	@echo "✅ Backend base image pushed to GHCR"

build-apps: build-backend-base ## Build only backend and frontend images (uses base image)
	@echo "🔨 Building application images (backend + frontend) with tag: $(GIT_SHA)"
	@echo "   Using local base image: ideaforge-ai-backend-base:latest"
	@docker build -f Dockerfile.backend \
		--build-arg GIT_SHA=$(GIT_SHA) \
		--build-arg VERSION=$(VERSION) \
		--build-arg BASE_IMAGE_TAG=latest \
		--build-arg BASE_IMAGE_REGISTRY=ideaforge-ai \
		-t ideaforge-ai-backend:$(GIT_SHA) .
	@docker build -f Dockerfile.frontend --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION) -t ideaforge-ai-frontend:$(GIT_SHA) .
	@echo "✅ Application images built: ideaforge-ai-backend:$(GIT_SHA) and ideaforge-ai-frontend:$(GIT_SHA)"

build-no-cache: ## Build Docker images without cache
	@echo "🔨 Building Docker images (no cache) with tag: $(GIT_SHA)"
	@docker build -f Dockerfile.backend --no-cache --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION) -t ideaforge-ai-backend:$(GIT_SHA) .
	@docker build -f Dockerfile.frontend --no-cache --build-arg GIT_SHA=$(GIT_SHA) --build-arg VERSION=$(VERSION) -t ideaforge-ai-frontend:$(GIT_SHA) .
	@echo "✅ Build complete"

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
EKS_IMAGE_TAG ?= latest  # Deprecated: Use BACKEND_IMAGE_TAG and FRONTEND_IMAGE_TAG instead
BACKEND_IMAGE_TAG ?= $(EKS_IMAGE_TAG)  # Backend image tag (e.g., fab20a2, latest, or specific version)
FRONTEND_IMAGE_TAG ?= $(EKS_IMAGE_TAG)  # Frontend image tag (e.g., e1dc1da, latest, or specific version)
EKS_STORAGE_CLASS ?= default-storage-class  # Default to default-storage-class (EBS), but can be overridden (e.g., gp2, gp3)
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

kind-update-images: ## Update image references in deployments for kind using latest git SHA
	@echo "🔄 Updating image references for kind cluster..."
	@echo "   Current Git SHA: $(GIT_SHA)"
	@BACKEND_IMAGE="ideaforge-ai-backend:$(GIT_SHA)"; \
	FRONTEND_IMAGE="ideaforge-ai-frontend:$(GIT_SHA)"; \
	\
	# Check if images with GIT_SHA tag exist, if not check for latest
	if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$${BACKEND_IMAGE}$$"; then \
		if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-backend:latest$$"; then \
			BACKEND_IMAGE="ideaforge-ai-backend:latest"; \
			echo "   ⚠️  Backend image with tag $(GIT_SHA) not found, using latest"; \
		else \
			echo "❌ Backend image not found. Please run 'make build-apps' first."; \
			exit 1; \
		fi; \
	else \
		echo "   ✅ Found backend image: $${BACKEND_IMAGE}"; \
	fi; \
	\
	if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$${FRONTEND_IMAGE}$$"; then \
		if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^ideaforge-ai-frontend:latest$$"; then \
			FRONTEND_IMAGE="ideaforge-ai-frontend:latest"; \
			echo "   ⚠️  Frontend image with tag $(GIT_SHA) not found, using latest"; \
		else \
			echo "❌ Frontend image not found. Please run 'make build-apps' first."; \
			exit 1; \
		fi; \
	else \
		echo "   ✅ Found frontend image: $${FRONTEND_IMAGE}"; \
	fi; \
	\
	# Update deployments directly using kubectl (no file modification needed)
	echo "   Updating backend deployment to use: $${BACKEND_IMAGE}"; \
	kubectl set image deployment/backend backend=$${BACKEND_IMAGE} -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) || \
		(echo "⚠️  Backend deployment not found, will be created on next apply" && true); \
	\
	echo "   Updating frontend deployment to use: $${FRONTEND_IMAGE}"; \
	kubectl set image deployment/frontend frontend=$${FRONTEND_IMAGE} -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) || \
		(echo "⚠️  Frontend deployment not found, will be created on next apply" && true); \
	\
	echo "✅ Image references updated: backend=$${BACKEND_IMAGE}, frontend=$${FRONTEND_IMAGE}"

rebuild-and-deploy-kind: build-apps kind-load-images kind-update-images ## Rebuild apps and deploy to kind cluster
	@echo "🚀 Rebuilding and deploying to kind cluster..."
	@if ! kubectl cluster-info --context kind-$(KIND_CLUSTER_NAME) &>/dev/null; then \
		echo "⚠️  Kind cluster not found. Creating cluster..."; \
		$(MAKE) kind-create kind-setup-ingress; \
	fi
	@$(MAKE) kind-deploy-internal
	@echo "✅ Deployment to kind complete!"

kind-deploy-full: ## Complete kind cluster setup: create cluster, setup ingress, build images, load secrets, deploy, seed database, verify access
	@echo "🚀 Complete Kind Cluster Setup"
	@echo "=============================="
	@echo ""
	@echo "Step 1: Checking Docker..."
	@docker info > /dev/null 2>&1 && echo "✅ Docker is running" || (echo "⚠️  Docker not running, attempting to start..." && open -a Docker 2>/dev/null && sleep 5 && timeout=30 elapsed=0 && while ! docker info > /dev/null 2>&1 && [ $$elapsed -lt $$timeout ]; do sleep 2; elapsed=$$((elapsed+2)); done && docker info > /dev/null 2>&1 && echo "✅ Docker is now running" || (echo "❌ Docker failed to start - please start Docker Desktop manually" && exit 1))
	@echo ""
	@echo "Step 2: Creating kind cluster..."
	@$(MAKE) kind-create
	@echo ""
	@echo "Step 3: Setting up ingress controller..."
	@$(MAKE) kind-setup-ingress
	@echo ""
	@echo "Step 4: Building application images..."
	@$(MAKE) build-apps
	@echo ""
	@echo "Step 5: Loading images into kind cluster..."
	@$(MAKE) kind-load-images
	@echo ""
	@echo "Step 6: Loading secrets from .env file..."
	@$(MAKE) kind-load-secrets
	@echo ""
	@echo "Step 7: Deploying application..."
	@$(MAKE) kind-update-images
	@$(MAKE) kind-deploy-internal
	@echo ""
	@echo "Step 8: Verifying access..."
	@$(MAKE) kind-verify-access
	@echo ""
	@echo "Step 9: Verifying demo accounts..."
	@$(MAKE) kind-verify-demo-accounts || echo "⚠️  Demo account verification failed - run 'make kind-seed-database' to seed accounts"
	@echo ""
	@echo "✅ Complete setup finished!"
	@echo ""
	@$(MAKE) kind-show-access-info
	@echo ""
	@echo "📝 Demo Account Credentials:"
	@echo "   Email: admin@ideaforge.ai (or user1@ideaforge.ai, user2@ideaforge.ai, etc.)"
	@echo "   Password: password123"
	@echo ""

kind-deploy: kind-create kind-setup-ingress kind-load-images ## Deploy to kind cluster (creates cluster, installs ingress, loads images, deploys)
	@echo "🚀 Deploying to kind cluster..."
	@$(MAKE) kind-update-images
	@$(MAKE) kind-deploy-internal

kind-create-db-configmaps: ## Create ConfigMaps for database migrations and seed data
	@echo "📦 Creating ConfigMaps for database setup..."
	@bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "✅ ConfigMaps created"

kind-load-secrets: ## Load secrets from .env file for kind deployment
	@if [ ! -f .env ] && [ ! -f env.kind ]; then \
		echo "⚠️  .env or env.kind file not found. Creating from env.kind.example..."; \
		if [ -f env.kind.example ]; then \
			cp env.kind.example env.kind; \
			echo "   Created env.kind from env.kind.example - please fill in your API keys!"; \
			echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN"; \
			exit 1; \
		else \
			echo "   env.kind.example not found. Please create env.kind manually."; \
			exit 1; \
		fi; \
	fi
	@ENV_FILE=$$([ -f env.kind ] && echo "env.kind" || echo ".env"); \
	echo "📦 Loading secrets from $$ENV_FILE file to Kubernetes..."; \
	bash $(K8S_DIR)/push-env-secret.sh $$ENV_FILE $(K8S_NAMESPACE) kind-$(KIND_CLUSTER_NAME)
	@echo "✅ Secrets pushed to Kubernetes secret: ideaforge-ai-secrets"

kind-deploy-internal: kind-create-db-configmaps ## Internal target: deploy manifests to kind (assumes cluster exists and images are loaded)
	@echo "📦 Applying Kubernetes manifests from k8s/kind/..."
	@if [ ! -d $(K8S_DIR)/kind ]; then \
		echo "❌ k8s/kind/ directory not found"; \
		exit 1; \
	fi
	@kubectl apply -f $(K8S_DIR)/kind/ --context kind-$(KIND_CLUSTER_NAME) --recursive
	@echo "📈 Applying HorizontalPodAutoscalers for auto-scaling..."
	@kubectl apply -f $(K8S_DIR)/kind/hpa-backend.yaml --context kind-$(KIND_CLUSTER_NAME) || echo "⚠️  HPA may not be available in kind cluster (requires metrics-server)"
	@kubectl apply -f $(K8S_DIR)/kind/hpa-frontend.yaml --context kind-$(KIND_CLUSTER_NAME) || echo "⚠️  HPA may not be available in kind cluster (requires metrics-server)"
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
	@echo "🌱 Running database seeding job..."
	@kubectl delete job db-seed -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --ignore-not-found=true
	@kubectl apply -f $(K8S_DIR)/kind/db-seed-job.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for database seeding job to complete..."
	@kubectl wait --for=condition=complete job/db-seed -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --timeout=120s || \
		(echo "⚠️  Database seeding job did not complete, checking logs..." && \
		 kubectl logs -n $(K8S_NAMESPACE) job/db-seed --context kind-$(KIND_CLUSTER_NAME) --tail=50 && \
		 echo "⚠️  Continuing anyway...")
	@echo "✅ Database seeding complete"
	@kubectl apply -f $(K8S_DIR)/backend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@kubectl apply -f $(K8S_DIR)/frontend.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for application pods to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=backend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(K8S_NAMESPACE) --timeout=300s --context kind-$(KIND_CLUSTER_NAME) || true
	@echo "🤖 Initializing Agno framework..."
	@$(MAKE) kind-agno-init || echo "⚠️  Agno initialization skipped"
	@echo "🌐 Applying ingress for kind..."
	@if [ -f $(K8S_DIR)/kind/ingress.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/kind/ingress.yaml --context kind-$(KIND_CLUSTER_NAME); \
	elif [ -f $(K8S_DIR)/ingress-kind.yaml ]; then \
		kubectl apply -f $(K8S_DIR)/ingress-kind.yaml --context kind-$(KIND_CLUSTER_NAME); \
	else \
		echo "⚠️  ingress-kind.yaml not found, using default ingress"; \
		kubectl apply -f $(K8S_DIR)/ingress.yaml --context kind-$(KIND_CLUSTER_NAME); \
	fi
	@echo "✅ Ingress applied"
	@echo ""
	@echo "✅ Deployment complete!"
	@echo ""
	@$(MAKE) kind-show-access-info
	@echo ""
	@$(MAKE) kind-status

kind-verify-access: ## Verify application access via ingress
	@echo "🔍 Verifying application access..."
	@INGRESS_PORT=$$(docker ps --filter "name=$(KIND_CLUSTER_NAME)-control-plane" --format "{{.Ports}}" | grep -o "0.0.0.0:[0-9]*->80" | cut -d: -f2 | cut -d- -f1 || echo "8080"); \
	echo "   Testing ingress on port $$INGRESS_PORT..."; \
	echo ""; \
	echo "   Testing frontend..."; \
	if curl -s -f http://localhost:$$INGRESS_PORT/ > /dev/null 2>&1; then \
		echo "   ✅ Frontend accessible at http://localhost:$$INGRESS_PORT/"; \
	else \
		echo "   ❌ Frontend not accessible"; \
	fi; \
	echo "   Testing backend health..."; \
	if curl -s -f http://localhost:$$INGRESS_PORT/health > /dev/null 2>&1; then \
		echo "   ✅ Backend health accessible at http://localhost:$$INGRESS_PORT/health"; \
	else \
		echo "   ❌ Backend health not accessible"; \
	fi; \
	echo "   Testing backend API..."; \
	if curl -s -f http://localhost:$$INGRESS_PORT/api/health > /dev/null 2>&1; then \
		echo "   ✅ Backend API accessible at http://localhost:$$INGRESS_PORT/api/"; \
	else \
		echo "   ❌ Backend API not accessible"; \
	fi; \
	echo ""

kind-verify-demo-accounts: ## Verify demo accounts exist and can login
	@echo "👥 Verifying Demo Accounts"
	@echo "=========================="
	@INGRESS_PORT=$$(docker ps --filter "name=$(KIND_CLUSTER_NAME)-control-plane" --format "{{.Ports}}" | grep -o "0.0.0.0:[0-9]*->80" | cut -d: -f2 | cut -d- -f1 || echo "8080"); \
	echo ""; \
	echo "1️⃣  Checking demo accounts in database..."; \
	POSTGRES_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POSTGRES_POD" ]; then \
		echo "   ❌ PostgreSQL pod not found"; \
		exit 1; \
	fi; \
	USER_COUNT=$$(kubectl exec -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) $$POSTGRES_POD -- psql -U agentic_pm -d agentic_pm_db -t -c "SELECT COUNT(*) FROM user_profiles WHERE email LIKE '%@ideaforge.ai';" 2>/dev/null | xargs || echo "0"); \
	if [ "$$USER_COUNT" -gt "0" ]; then \
		echo "   ✅ Found $$USER_COUNT demo accounts"; \
		kubectl exec -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) $$POSTGRES_POD -- psql -U agentic_pm -d agentic_pm_db -c "SELECT email, full_name, is_active FROM user_profiles WHERE email LIKE '%@ideaforge.ai' ORDER BY email LIMIT 5;" 2>/dev/null | grep -E "@ideaforge.ai|Admin|User" | head -5 || true; \
	else \
		echo "   ⚠️  No demo accounts found. Run 'make kind-seed-database' to seed demo accounts."; \
	fi; \
	echo ""; \
	echo "2️⃣  Testing demo account login..."; \
	LOGIN_RESPONSE=$$(curl -s -X POST http://localhost:$$INGRESS_PORT/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@ideaforge.ai","password":"password123"}' 2>/dev/null); \
	if echo "$$LOGIN_RESPONSE" | grep -q "token"; then \
		TOKEN=$$(echo "$$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4); \
		if [ -n "$$TOKEN" ]; then \
			echo "   ✅ Demo account login successful (admin@ideaforge.ai)"; \
			echo "   Testing authenticated API call..."; \
			USER_INFO=$$(curl -s http://localhost:$$INGRESS_PORT/api/auth/me -H "Authorization: Bearer $$TOKEN" 2>/dev/null); \
			if echo "$$USER_INFO" | grep -q "email"; then \
				USER_EMAIL=$$(echo "$$USER_INFO" | grep -o '"email":"[^"]*"' | cut -d'"' -f4); \
				USER_NAME=$$(echo "$$USER_INFO" | grep -o '"full_name":"[^"]*"' | cut -d'"' -f4); \
				echo "   ✅ Authenticated API call successful"; \
				echo "   User: $$USER_NAME ($$USER_EMAIL)"; \
			else \
				echo "   ⚠️  Authenticated API call failed"; \
			fi; \
		else \
			echo "   ❌ Login failed - no token received"; \
		fi; \
	else \
		echo "   ❌ Demo account login failed"; \
		echo "   Response: $$LOGIN_RESPONSE" | head -3; \
	fi; \
	echo ""; \
	echo "3️⃣  Testing additional demo accounts..."; \
	for email in user1@ideaforge.ai user2@ideaforge.ai; do \
		TEST_RESPONSE=$$(curl -s -X POST http://localhost:$$INGRESS_PORT/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"$$email\",\"password\":\"password123\"}" 2>/dev/null); \
		if echo "$$TEST_RESPONSE" | grep -q "token"; then \
			echo "   ✅ $$email login successful"; \
		else \
			echo "   ⚠️  $$email login failed"; \
		fi; \
	done; \
	echo ""; \
	echo "✅ Demo account verification complete"

kind-show-access-info: ## Show all access methods for the application
	@echo "🌐 Application Access Information"
	@echo "================================"
	@INGRESS_PORT=$$(docker ps --filter "name=$(KIND_CLUSTER_NAME)-control-plane" --format "{{.Ports}}" | grep -o "0.0.0.0:[0-9]*->80" | cut -d: -f2 | cut -d- -f1 || echo "8080"); \
	echo ""; \
	echo "📍 Primary Access Method (Ingress on port $$INGRESS_PORT):"; \
	echo "   Frontend:     http://localhost:$$INGRESS_PORT/"; \
	echo "   Backend API:  http://localhost:$$INGRESS_PORT/api/"; \
	echo "   Health Check: http://localhost:$$INGRESS_PORT/health"; \
	echo "   Swagger Docs: http://localhost:$$INGRESS_PORT/api/docs"; \
	echo ""; \
	echo "📍 Alternative Access Methods:"; \
	echo "   1. With host headers:"; \
	echo "      Frontend: curl -H 'Host: ideaforge.local' http://localhost:$$INGRESS_PORT/"; \
	echo "      Backend:  curl -H 'Host: api.ideaforge.local' http://localhost:$$INGRESS_PORT/"; \
	echo ""; \
	echo "   2. Add to /etc/hosts (then use hostnames):"; \
	echo "      sudo sh -c 'echo \"127.0.0.1 ideaforge.local api.ideaforge.local\" >> /etc/hosts'"; \
	echo "      Frontend: http://ideaforge.local:$$INGRESS_PORT"; \
	echo "      Backend:  http://api.ideaforge.local:$$INGRESS_PORT"; \
	echo ""; \
	echo "   3. Port forward (separate ports):"; \
	echo "      make kind-port-forward"; \
	echo "      Frontend: http://localhost:3001"; \
	echo "      Backend:  http://localhost:8000"; \
	echo ""

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

kind-cleanup-replicasets: ## Clean up old replicasets with 0 replicas
	@echo "🧹 Cleaning up old replicasets..."
	@kubectl get replicasets -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o json 2>/dev/null | \
		jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' | \
		while read rs; do \
			if [ -n "$$rs" ]; then \
				echo "   Deleting replicaset: $$rs"; \
				kubectl delete replicaset $$rs -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --ignore-not-found=true; \
			fi; \
		done || echo "⚠️  No replicasets to clean up or cluster not accessible"
	@echo "✅ Replicaset cleanup complete"

kind-check-logs-before-commit: ## Check all pod logs for errors and Agno initialization (run before commit)
	@echo "🔍 Checking pod logs before commit..."
	@echo ""
	@echo "=== Backend Logs (Errors) ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) --tail=200 2>/dev/null | \
		grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | \
		grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found"
	@echo ""
	@echo "=== Agno Initialization Status ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) --tail=200 2>/dev/null | \
		grep -E "(agno.*initialized|agno_enabled.*true|agno_orchestrator_initialized)" | tail -5 || \
		echo "⚠️  Agno initialization not found in logs"
	@echo ""
	@echo "=== Frontend Logs (Errors) ==="
	@kubectl logs -n $(K8S_NAMESPACE) -l app=frontend --context kind-$(KIND_CLUSTER_NAME) --tail=200 2>/dev/null | \
		grep -iE "(error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED|critical|Critical|CRITICAL|fatal|Fatal|FATAL)" | \
		grep -v "warning" | grep -v "WARNING" | head -20 || echo "✅ No errors found"
	@echo ""
	@echo "✅ Log check complete"

verify-kind-complete: ## Complete verification: pods, replicasets, image tags, secrets, Agno initialization, demo accounts
	@echo "🔍 Complete Verification for Kind Cluster"
	@echo "=========================================="
	@echo ""
	@echo "1️⃣  Checking Pod Status..."
	@kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null || (echo "❌ Cluster not accessible"; exit 1)
	@echo ""
	@echo "2️⃣  Checking for Old Replicasets..."
	@OLD_RS=$$(kubectl get replicasets -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o json 2>/dev/null | \
		jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' | wc -l | tr -d ' '); \
	if [ "$$OLD_RS" -gt 0 ]; then \
		echo "⚠️  Found $$OLD_RS old replicasets. Run 'make kind-cleanup-replicasets' to clean up"; \
	else \
		echo "✅ No old replicasets found"; \
	fi
	@echo ""
	@echo "3️⃣  Checking Image Tags..."
	@CURRENT_SHA=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown"); \
	BACKEND_IMAGE=$$(kubectl get deployment backend -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null); \
	FRONTEND_IMAGE=$$(kubectl get deployment frontend -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null); \
	echo "   Current Git SHA: $$CURRENT_SHA"; \
	echo "   Backend Image: $$BACKEND_IMAGE"; \
	echo "   Frontend Image: $$FRONTEND_IMAGE"; \
	if echo "$$BACKEND_IMAGE" | grep -q "$$CURRENT_SHA" && echo "$$FRONTEND_IMAGE" | grep -q "$$CURRENT_SHA"; then \
		echo "✅ Image tags match current git SHA"; \
	else \
		echo "⚠️  Image tags may not match current git SHA"; \
	fi
	@echo ""
	@echo "4️⃣  Checking Docker Config Secrets..."
	@kubectl get secrets -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null | grep dockerconfig || echo "ℹ️  No dockerconfig secrets (using public images)"
	@echo ""
	@echo "5️⃣  Checking Agno Initialization..."
	@kubectl logs -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) --tail=100 2>/dev/null | \
		grep -E "(agno.*initialized|agno_enabled.*true|agno_orchestrator_initialized)" | tail -3 || \
		echo "⚠️  Agno initialization not found in logs"
	@echo ""
	@echo "6️⃣  Checking Provider Configuration..."
	@kubectl exec -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -- \
		python -c "from backend.services.provider_registry import provider_registry; print('Providers:', provider_registry.get_configured_providers())" 2>/dev/null | \
		grep -v "warning\|no_embedder" | tail -1 || echo "⚠️  Could not check provider configuration"
	@echo ""
	@echo "7️⃣  Verifying Application Access..."
	@$(MAKE) kind-verify-access
	@echo ""
	@echo "8️⃣  Verifying Demo Accounts..."
	@$(MAKE) kind-verify-demo-accounts || echo "⚠️  Demo account verification failed"
	@echo ""
	@echo "✅ Verification complete"

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

kind-update-db-configmaps: ## Update database ConfigMaps in Kind with latest seed file
	@echo "📦 Updating database ConfigMaps in Kind cluster..."
	@K8S_NAMESPACE=$(K8S_NAMESPACE) bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "✅ ConfigMaps updated"

kind-seed-database: ## Run database seeding job in Kind cluster (can be invoked separately)
	@echo "🌱 Running database seeding job in Kind cluster..."
	@if ! kubectl get namespace $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) &>/dev/null; then \
		echo "❌ Namespace $(K8S_NAMESPACE) does not exist"; \
		echo "   Please deploy the application first: make kind-deploy"; \
		exit 1; \
	fi
	@kubectl delete job db-seed -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --ignore-not-found=true
	@kubectl apply -f $(K8S_DIR)/kind/db-seed-job.yaml --context kind-$(KIND_CLUSTER_NAME)
	@echo "⏳ Waiting for database seeding job to complete..."
	@kubectl wait --for=condition=complete job/db-seed -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --timeout=120s || \
		(echo "⚠️  Database seeding job did not complete, checking logs..." && \
		 kubectl logs -n $(K8S_NAMESPACE) job/db-seed --context kind-$(KIND_CLUSTER_NAME) --tail=50 && \
		 exit 1)
	@echo "✅ Database seeding complete"
	@echo "📊 Verifying seeded data..."
	@kubectl logs -n $(K8S_NAMESPACE) job/db-seed --context kind-$(KIND_CLUSTER_NAME) --tail=20 | grep -E "tenants|demo_users|products" || true

kind-add-demo-accounts: ## Add demo accounts to existing Kind database (legacy method, use kind-seed-database instead)
	@echo "👥 Adding demo accounts to Kind database..."
	@POSTGRES_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POSTGRES_POD" ]; then \
		echo "❌ PostgreSQL pod not found in namespace $(K8S_NAMESPACE)"; \
		exit 1; \
	fi; \
	echo "   Using PostgreSQL pod: $$POSTGRES_POD"; \
	kubectl cp $(K8S_DIR)/add-demo-accounts.sql $(K8S_NAMESPACE)/$$POSTGRES_POD:/tmp/add-demo-accounts.sql --context kind-$(KIND_CLUSTER_NAME); \
	kubectl exec -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) $$POSTGRES_POD -- psql -U agentic_pm -d agentic_pm_db -f /tmp/add-demo-accounts.sql; \
	echo "✅ Demo accounts added successfully"

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
	@echo "⚠️  Note: Namespace $(EKS_NAMESPACE) must already exist in the cluster"
	@if ! kubectl get namespace $(EKS_NAMESPACE) &>/dev/null; then \
		echo "❌ Namespace $(EKS_NAMESPACE) does not exist"; \
		echo "   Please create it first or ensure it exists in your EKS cluster"; \
		exit 1; \
	fi
	@echo "🔐 Creating docker-registry secret for GitHub Container Registry..."
	@GITHUB_USERNAME="$${EKS_GITHUB_USERNAME:-soumantrivedi}"; \
	GITHUB_TOKEN=""; \
	if [ -n "$$EKS_GITHUB_TOKEN" ]; then \
		GITHUB_TOKEN="$$EKS_GITHUB_TOKEN"; \
		echo "   Using GITHUB_TOKEN from EKS_GITHUB_TOKEN environment variable"; \
	elif [ -f .env ] || [ -f env.eks ]; then \
		ENV_FILE=$$([ -f env.eks ] && echo "env.eks" || echo ".env"); \
		GITHUB_TOKEN=$$(grep "^GITHUB_TOKEN=" $$ENV_FILE 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs || echo ""); \
		if [ -n "$$GITHUB_TOKEN" ]; then \
			echo "   Using GITHUB_TOKEN from $$ENV_FILE file"; \
		fi; \
	fi; \
	if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "❌ GITHUB_TOKEN (GitHub PAT) is required"; \
		echo "   Options:"; \
		echo "   1. Export: export EKS_GITHUB_TOKEN=ghp_your_pat_token_here"; \
		echo "   2. Add to env.eks: GITHUB_TOKEN=ghp_your_pat_token_here"; \
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

eks-prepare-namespace: ## Prepare namespace-specific manifests for EKS (updates namespace and image tags in all manifests)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-deploy-full EKS_NAMESPACE=your-namespace [BACKEND_IMAGE_TAG=tag] [FRONTEND_IMAGE_TAG=tag]"; \
		echo "   Example: make eks-deploy-full EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 BACKEND_IMAGE_TAG=fab20a2 FRONTEND_IMAGE_TAG=e1dc1da"; \
		exit 1; \
	fi
	@echo "📝 Preparing EKS deployment for namespace: $(EKS_NAMESPACE)"
	@if [ ! -d $(K8S_DIR)/eks ]; then \
		echo "❌ k8s/eks/ directory not found"; \
		exit 1; \
	fi
	@echo "📝 Updating namespace, image tags, and storage class in EKS manifests..."
	@echo "   Backend Image Tag: $(BACKEND_IMAGE_TAG)"
	@echo "   Frontend Image Tag: $(FRONTEND_IMAGE_TAG)"
	@python3 $(K8S_DIR)/update-eks-namespace.py $(K8S_DIR)/eks $(EKS_NAMESPACE) $(BACKEND_IMAGE_TAG) $(FRONTEND_IMAGE_TAG) $(EKS_STORAGE_CLASS) || \
		(echo "⚠️  Python script failed, trying sed fallback..." && \
		 for file in $$(find $(K8S_DIR)/eks -name "*.yaml" -type f); do \
			if [ "$$(uname)" = "Darwin" ]; then \
				sed -i '' "s|namespace: ideaforge-ai|namespace: $(EKS_NAMESPACE)|g" "$$file"; \
				sed -i '' "s|name: ideaforge-ai$$|name: $(EKS_NAMESPACE)|g" "$$file"; \
				sed -i '' "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" "$$file"; \
				sed -i '' "s|ghcr\.io/soumantrivedi/ideaforge-ai/frontend:.*|ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(FRONTEND_IMAGE_TAG)|g" "$$file"; \
			else \
				sed -i "s|namespace: ideaforge-ai|namespace: $(EKS_NAMESPACE)|g" "$$file"; \
				sed -i "s|name: ideaforge-ai$$|name: $(EKS_NAMESPACE)|g" "$$file"; \
				sed -i "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" "$$file"; \
				sed -i "s|ghcr\.io/soumantrivedi/ideaforge-ai/frontend:.*|ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(FRONTEND_IMAGE_TAG)|g" "$$file"; \
			fi; \
		 done)
	@echo "✅ EKS manifests prepared for namespace: $(EKS_NAMESPACE)"

eks-load-secrets: ## Load secrets from .env file for EKS deployment (use EKS_NAMESPACE=your-namespace)
	@if [ ! -f .env ] && [ ! -f env.eks ]; then \
		echo "⚠️  .env or env.eks file not found. Creating from env.eks.example..."; \
		if [ -f env.eks.example ]; then \
			cp env.eks.example env.eks; \
			echo "   Created env.eks from env.eks.example - please fill in your API keys!"; \
			echo "   Required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN"; \
			exit 1; \
		else \
			echo "   env.eks.example not found. Please create env.eks manually."; \
			exit 1; \
		fi; \
	fi
	@ENV_FILE=$$([ -f env.eks ] && echo "env.eks" || echo ".env"); \
	echo "📦 Loading secrets from $$ENV_FILE file to Kubernetes..."; \
	bash $(K8S_DIR)/push-env-secret.sh $$ENV_FILE $(EKS_NAMESPACE)
	@echo "✅ Secrets pushed to Kubernetes secret: ideaforge-ai-secrets in namespace: $(EKS_NAMESPACE)"

eks-deploy-full: eks-setup-ghcr-secret eks-prepare-namespace eks-load-secrets eks-deploy ## Full EKS deployment with GHCR setup (use EKS_NAMESPACE=your-namespace, BACKEND_IMAGE_TAG=tag, FRONTEND_IMAGE_TAG=tag)

eks-port-forward: ## Port-forward to EKS services (use EKS_NAMESPACE=your-namespace, KUBECONFIG=path/to/kubeconfig)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-port-forward EKS_NAMESPACE=your-namespace [KUBECONFIG=path/to/kubeconfig]"; \
		exit 1; \
	fi
	@echo "🔌 Setting up port forwarding for EKS namespace: $(EKS_NAMESPACE)"
	@if [ -n "$(KUBECONFIG)" ]; then \
		echo "   Using KUBECONFIG: $(KUBECONFIG)"; \
		export KUBECONFIG=$(KUBECONFIG); \
	fi
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend API: http://localhost:8000"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	@kubectl port-forward -n $(EKS_NAMESPACE) service/frontend 3000:3000 > /dev/null 2>&1 & \
	 kubectl port-forward -n $(EKS_NAMESPACE) service/backend 8000:8000 > /dev/null 2>&1 & \
	 sleep 2 && \
	 echo "✅ Port forwarding active" && \
	 echo "   To stop: pkill -f 'kubectl port-forward'" && \
	 wait

eks-deploy: eks-prepare-namespace ## Deploy to EKS cluster (use EKS_NAMESPACE=your-namespace, BACKEND_IMAGE_TAG=tag, FRONTEND_IMAGE_TAG=tag)
	@echo "☁️  Deploying to EKS cluster: $(EKS_CLUSTER_NAME)"
	@echo "📦 Namespace: $(EKS_NAMESPACE)"
	@echo "🏷️  Image Registry: $(EKS_IMAGE_REGISTRY)"
	@echo "🏷️  Backend Image Tag: $(BACKEND_IMAGE_TAG)"
	@echo "🏷️  Frontend Image Tag: $(FRONTEND_IMAGE_TAG)"
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "❌ kubectl is not configured or EKS cluster is not accessible"; \
		echo "   Configure kubectl: aws eks update-kubeconfig --name $(EKS_CLUSTER_NAME) --region $(EKS_REGION)"; \
		exit 1; \
	fi
	@echo "✅ kubectl is configured"
	@echo "📦 Creating ConfigMaps for database setup..."
	@EKS_NAMESPACE=$(EKS_NAMESPACE) bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "📦 Applying Kubernetes manifests from k8s/eks/ to namespace: $(EKS_NAMESPACE)"
	@echo "⚠️  Note: Namespace $(EKS_NAMESPACE) must already exist in the cluster"
	@echo "   (Skipping namespace.yaml - namespace must be pre-created)"
	@find $(K8S_DIR)/eks -name "*.yaml" ! -name "namespace.yaml" -type f -exec kubectl apply -f {} \;
	@echo "⏳ Waiting for database services to be ready..."
	@kubectl wait --for=condition=ready pod -l app=postgres -n $(EKS_NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=ready pod -l app=redis -n $(EKS_NAMESPACE) --timeout=120s || true
	@echo "🔄 Running database setup (migrations + seeding)..."
	@kubectl apply -f $(K8S_DIR)/eks/db-setup-job.yaml
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
	@BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- \
			sh -c "nc -z redis 6379 && echo '✅ Redis reachable' || echo '❌ Redis not reachable'"; \
	fi
	@echo ""
	@echo "3️⃣  Testing Backend Health Endpoint..."
	@BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- \
			curl -s http://localhost:8000/health | head -20 || echo "❌ Health check failed"; \
	fi
	@echo ""
	@echo "✅ Service-to-service tests complete!"

eks-update-db-configmaps: ## Update database ConfigMaps in EKS with latest seed file (use EKS_NAMESPACE=your-namespace)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-update-db-configmaps EKS_NAMESPACE=your-namespace"; \
		exit 1; \
	fi
	@echo "📦 Updating database ConfigMaps in EKS namespace: $(EKS_NAMESPACE)"
	@EKS_NAMESPACE=$(EKS_NAMESPACE) bash $(K8S_DIR)/create-db-configmaps.sh
	@echo "✅ ConfigMaps updated"

eks-add-demo-accounts: ## Add demo accounts to existing EKS database (use EKS_NAMESPACE=your-namespace)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-add-demo-accounts EKS_NAMESPACE=your-namespace"; \
		exit 1; \
	fi
	@echo "👥 Adding demo accounts to EKS database in namespace: $(EKS_NAMESPACE)"
	@if [ -n "$(KUBECONFIG)" ]; then \
		export KUBECONFIG=$(KUBECONFIG); \
	fi
	@POSTGRES_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POSTGRES_POD" ]; then \
		echo "❌ PostgreSQL pod not found in namespace $(EKS_NAMESPACE)"; \
		exit 1; \
	fi; \
	echo "   Using PostgreSQL pod: $$POSTGRES_POD"; \
	kubectl cp $(K8S_DIR)/add-demo-accounts.sql $(EKS_NAMESPACE)/$$POSTGRES_POD:/tmp/add-demo-accounts.sql; \
	kubectl exec -n $(EKS_NAMESPACE) $$POSTGRES_POD -- psql -U agentic_pm -d agentic_pm_db -f /tmp/add-demo-accounts.sql; \
	echo "✅ Demo accounts added successfully"

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
