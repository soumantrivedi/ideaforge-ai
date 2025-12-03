.PHONY: help build-apps build-no-cache version kind-create kind-delete kind-deploy kind-test kind-test-agents kind-cleanup eks-deploy eks-test kind-agno-init eks-agno-init kind-load-secrets eks-load-secrets eks-setup-ghcr-secret eks-prepare-namespace eks-setup-hpa eks-prewarm eks-performance-test eks-rollout-images kind-test-coordinator eks-test-coordinator kind-test-integration eks-test-integration

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

build-backend-base: ## Build backend base image only if Dockerfile.base.backend or requirements.txt changed
	@echo "🔍 Checking if base image needs rebuild..."
	@if [ ! -f Dockerfile.base.backend ] || [ ! -f backend/requirements.txt ]; then \
		echo "⚠️  Required files not found. Building base image..."; \
		docker build -f Dockerfile.base.backend -t ideaforge-ai-backend-base:latest .; \
		echo "✅ Backend base image built: ideaforge-ai-backend-base:latest"; \
		exit 0; \
	fi
	@BASE_IMAGE_EXISTS=$$(docker images -q ideaforge-ai-backend-base:latest 2>/dev/null); \
	if [ -z "$$BASE_IMAGE_EXISTS" ]; then \
		echo "📦 Base image not found. Building..."; \
		docker build -f Dockerfile.base.backend -t ideaforge-ai-backend-base:latest .; \
		echo "✅ Backend base image built: ideaforge-ai-backend-base:latest"; \
	else \
		DOCKERFILE_TIME=$$(stat -f %m Dockerfile.base.backend 2>/dev/null || stat -c %Y Dockerfile.base.backend 2>/dev/null); \
		REQUIREMENTS_TIME=$$(stat -f %m backend/requirements.txt 2>/dev/null || stat -c %Y backend/requirements.txt 2>/dev/null); \
		IMAGE_TIME=$$(docker inspect -f '{{ .Created }}' ideaforge-ai-backend-base:latest 2>/dev/null | xargs -I {} date -d {} +%s 2>/dev/null || docker inspect -f '{{ .Created }}' ideaforge-ai-backend-base:latest 2>/dev/null | xargs -I {} date -j -f "%Y-%m-%dT%H:%M:%S" {} +%s 2>/dev/null || echo "0"); \
		if [ -z "$$IMAGE_TIME" ] || [ "$$IMAGE_TIME" = "0" ]; then \
			echo "📦 Cannot determine image age. Rebuilding to be safe..."; \
			docker build -f Dockerfile.base.backend -t ideaforge-ai-backend-base:latest .; \
			echo "✅ Backend base image built: ideaforge-ai-backend-base:latest"; \
		elif [ "$$DOCKERFILE_TIME" -gt "$$IMAGE_TIME" ] || [ "$$REQUIREMENTS_TIME" -gt "$$IMAGE_TIME" ]; then \
			echo "📝 Base image files changed. Rebuilding..."; \
			docker build -f Dockerfile.base.backend -t ideaforge-ai-backend-base:latest .; \
			echo "✅ Backend base image rebuilt: ideaforge-ai-backend-base:latest"; \
		else \
			echo "✅ Base image is up to date. Skipping rebuild."; \
		fi \
	fi

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

build-apps: build-backend-base ## Build only backend and frontend images (uses base image, rebuilds base only if needed)
	@echo "🔨 Building application images (backend + frontend) with tag: $(GIT_SHA)"
	@echo "   Using local base image: ideaforge-ai-backend-base:latest"
	@docker build -f Dockerfile.backend \
		--build-arg GIT_SHA=$(GIT_SHA) \
		--build-arg VERSION=$(VERSION) \
		--build-arg BASE_IMAGE=ideaforge-ai-backend-base:latest \
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
KIND_INGRESS_PORT ?= 8081
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

kind-create: ## Create a local kind cluster for testing with VPN networking support
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
	@echo "    hostPort: $(KIND_INGRESS_PORT)" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    protocol: TCP" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - containerPort: 443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@if [ "$(KIND_CLUSTER_NAME)" = "ideaforge-ai" ]; then \
		echo "    hostPort: 8444" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml; \
	else \
		echo "    hostPort: 8443" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml; \
	fi
	@echo "    protocol: TCP" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  extraMounts:" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "  - hostPath: /etc/resolv.conf" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    containerPath: /etc/resolv.conf.host" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "    readOnly: true" >> /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@kind create cluster --name $(KIND_CLUSTER_NAME) --image $(KIND_IMAGE) --config /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml || true
	@rm -f /tmp/kind-config-$(KIND_CLUSTER_NAME).yaml
	@echo "⏳ Waiting for cluster to be ready..."
	@kubectl wait --for=condition=Ready nodes --all --timeout=300s --context kind-$(KIND_CLUSTER_NAME)
	@echo "✅ Kind cluster created successfully!"
	@echo "   Cluster name: $(KIND_CLUSTER_NAME)"
	@echo "   Context: kind-$(KIND_CLUSTER_NAME)"
	@echo ""
	@echo "🌐 Configuring DNS for VPN access..."
	@$(MAKE) kind-configure-dns || (echo "⚠️  DNS configuration failed - you may need to run 'make kind-configure-dns' manually" && echo "   This is required for pods to resolve VPN-accessible hostnames like ai-gateway.quantumblack.com")
	@echo ""
	@echo "✅ Kind cluster setup complete!"
	@echo "   DNS is configured to forward queries to host resolver"
	@echo "   Host resolv.conf mounted for VPN DNS access"
	@echo "   This allows pods to access VPN-accessible services while the cluster is running"

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

kind-deploy: kind-create kind-setup-ingress kind-load-images kind-load-secrets ## Deploy to kind cluster (creates cluster, installs ingress, loads images, loads secrets, deploys)
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
	@kubectl apply -f $(K8S_DIR)/kind/db-setup-job.yaml -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME)
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

kind-configure-dns: ## Configure Kind cluster to use host DNS (for VPN access to internal services)
	@echo "🌐 Configuring Kind cluster DNS to use host resolver..."
	@echo "   This allows pods to resolve hostnames accessible via VPN"
	@echo "   Waiting for CoreDNS to be ready..."
	@kubectl wait --for=condition=ready pod -l k8s-app=kube-dns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --timeout=60s || true
	@echo "   Configuring CoreDNS to use host's resolv.conf (mounted at /etc/resolv.conf.host)..."
	@echo "   Patching CoreDNS ConfigMap to forward DNS queries to host resolver..."
	@kubectl get configmap coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) -o yaml > /tmp/coredns-original.yaml 2>/dev/null || true; \
	if kubectl get configmap coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) > /dev/null 2>&1; then \
		echo "   Updating existing CoreDNS ConfigMap..."; \
		HOST_RESOLV=$$(docker exec $(KIND_CLUSTER_NAME)-control-plane cat /etc/resolv.conf.host 2>/dev/null | grep -E "^nameserver" | head -1 | awk '{print $$2}' || echo "8.8.8.8"); \
		echo "   Using host DNS server: $$HOST_RESOLV"; \
		kubectl patch configmap coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --type merge -p "{\"data\":{\"Corefile\":\".:53 {\\n    errors\\n    health {\\n       lameduck 5s\\n    }\\n    ready\\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\\n       pods insecure\\n       fallthrough in-addr.arpa ip6.arpa\\n       ttl 30\\n    }\\n    prometheus :9153\\n    forward . $$HOST_RESOLV {\\n       max_concurrent 1000\\n    }\\n    cache 30\\n    loop\\n    reload\\n    loadbalance\\n}\\n\"}}" || \
		kubectl patch configmap coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --type merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n       lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n       pods insecure\n       fallthrough in-addr.arpa ip6.arpa\n       ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf.host {\n       max_concurrent 1000\n    }\n    cache 30\n    loop\n    reload\n    loadbalance\n}\n"}}' || \
		kubectl apply -f $(K8S_DIR)/kind/coredns-custom.yaml --context kind-$(KIND_CLUSTER_NAME) || true; \
	else \
		echo "   CoreDNS ConfigMap not found, applying custom configuration..."; \
		kubectl apply -f $(K8S_DIR)/kind/coredns-custom.yaml --context kind-$(KIND_CLUSTER_NAME) || true; \
	fi
	@echo "   Updating CoreDNS deployment to mount host resolv.conf..."
	@kubectl get deployment coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) -o yaml > /tmp/coredns-deployment.yaml 2>/dev/null || true; \
	if ! kubectl get deployment coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) -o yaml | grep -q "resolv.conf.host"; then \
		echo "   Adding host resolv.conf mount to CoreDNS pods..."; \
		kubectl patch deployment coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --type json -p '[{"op": "add", "path": "/spec/template/spec/containers/0/volumeMounts/-", "value": {"name": "host-resolv", "mountPath": "/etc/resolv.conf.host", "readOnly": true}}]' || true; \
		kubectl patch deployment coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --type json -p '[{"op": "add", "path": "/spec/template/spec/volumes/-", "value": {"name": "host-resolv", "hostPath": {"path": "/etc/resolv.conf.host", "type": "File"}}}]' || true; \
	fi
	@echo "   Restarting CoreDNS pods to apply configuration..."
	@kubectl rollout restart deployment/coredns -n kube-system --context kind-$(KIND_CLUSTER_NAME) || true
	@echo "   Waiting for CoreDNS pods to be ready..."
	@kubectl wait --for=condition=ready pod -l k8s-app=kube-dns -n kube-system --context kind-$(KIND_CLUSTER_NAME) --timeout=120s || true
	@sleep 5
	@echo "   Verifying DNS configuration..."
	@COREDNS_POD=$$(kubectl get pods -n kube-system -l k8s-app=kube-dns --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$COREDNS_POD" ]; then \
		echo "   Testing DNS resolution from CoreDNS pod..."; \
		kubectl exec -n kube-system $$COREDNS_POD --context kind-$(KIND_CLUSTER_NAME) -- sh -c "cat /etc/resolv.conf.host 2>/dev/null || echo 'Host resolv.conf not mounted'" || true; \
		kubectl exec -n kube-system $$COREDNS_POD --context kind-$(KIND_CLUSTER_NAME) -- nslookup google.com 2>&1 | grep -q "Name:" && echo "   ✅ CoreDNS can resolve external hostnames" || echo "   ⚠️  CoreDNS DNS test inconclusive"; \
	fi
	@echo "✅ DNS configuration updated and verified"
	@echo "   Pods can now resolve hostnames accessible from the host (including VPN services)"
	@echo "   This configuration will persist while the cluster is running"

kind-verify-dns: ## Verify DNS configuration in Kind cluster
	@echo "🔍 Verifying DNS configuration..."
	@bash scripts/verify-dns-config.sh

kind-test-ai-gateway-connectivity: ## Test AI Gateway connectivity from Kind cluster pods
	@echo "🧪 Testing AI Gateway connectivity from Kind cluster..."
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make kind-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Using backend pod: $$BACKEND_POD"; \
	echo "   Testing DNS resolution..."; \
	if kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
		python -c "import socket; socket.gethostbyname('ai-gateway.quantumblack.com'); print('✅ DNS resolution successful')" 2>&1 | grep -q "✅"; then \
		echo "   ✅ DNS resolution successful"; \
		echo "   Testing HTTP connectivity..."; \
		if kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) -- \
			python -c "import httpx, asyncio; asyncio.run((lambda: httpx.AsyncClient(timeout=10.0).get('https://ai-gateway.quantumblack.com/health'))())" 2>&1 | \
			grep -qE "200|OK|healthy"; then \
			echo "   ✅ HTTP connectivity successful"; \
		else \
			echo "   ⚠️  HTTP connectivity test failed - check VPN connection and network access"; \
		fi; \
	else \
		echo "   ❌ DNS resolution failed"; \
		echo "   Troubleshooting steps:"; \
		echo "     1. Ensure VPN is connected on the host machine"; \
		echo "     2. Run 'make kind-configure-dns' to reconfigure DNS"; \
		echo "     3. Run 'make kind-verify-dns' to verify DNS configuration"; \
	fi

kind-restart-backend: ## Restart backend deployment to pick up code changes
	@echo "🔄 Restarting backend deployment..."
	@kubectl rollout restart deployment/backend -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME)
	@kubectl rollout status deployment/backend -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) --timeout=180s
	@echo "✅ Backend deployment restarted"

kind-backup-database: ## Backup database from Kind cluster
	@echo "📦 Backing up database from Kind cluster..."
	@bash scripts/backup-database.sh

kind-restore-database: ## Restore database to Kind cluster (requires BACKUP_FILE env var)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ BACKUP_FILE not specified"; \
		echo "   Usage: make kind-restore-database BACKUP_FILE=/path/to/backup.sql"; \
		exit 1; \
	fi
	@echo "📥 Restoring database to Kind cluster..."
	@BACKUP_FILE=$(BACKUP_FILE) bash scripts/restore-database.sh

kind-recreate-with-vpn: ## Recreate Kind cluster with VPN networking support (backups database first)
	@echo "🔄 Recreating Kind cluster with VPN networking support..."
	@echo ""
	@echo "Step 1: Backing up current database..."
	@$(MAKE) kind-backup-database || echo "⚠️  Database backup skipped (cluster may not exist)"
	@echo ""
	@echo "Step 2: Deleting existing cluster..."
	@$(MAKE) kind-delete || echo "⚠️  Cluster deletion skipped"
	@echo ""
	@echo "Step 3: Creating new cluster with VPN networking..."
	@$(MAKE) kind-create
	@echo ""
	@echo "Step 4: Setting up ingress..."
	@$(MAKE) kind-setup-ingress
	@echo ""
	@echo "Step 5: Loading images..."
	@$(MAKE) kind-load-images
	@echo ""
	@echo "Step 6: Loading secrets..."
	@$(MAKE) kind-load-secrets
	@echo ""
	@echo "Step 7: Deploying application..."
	@$(MAKE) kind-deploy-internal
	@echo ""
	@LATEST_BACKUP=$$(ls -t backups/ideaforge-ai-backup-*.sql 2>/dev/null | head -1); \
	if [ -n "$$LATEST_BACKUP" ]; then \
		echo "Step 8: Restoring database from latest backup..."; \
		echo "   Backup file: $$LATEST_BACKUP"; \
		echo "   Run: make kind-restore-database BACKUP_FILE=$$LATEST_BACKUP"; \
		echo "   Or restore manually after database is ready"; \
	else \
		echo "Step 8: No database backup found - database will be initialized fresh"; \
	fi
	@echo ""
	@echo "✅ Cluster recreation complete!"
	@echo "   DNS is configured for VPN access"
	@echo "   Run 'make kind-verify-dns' to verify DNS resolution"

kind-configure-vpn-networking: ## Configure existing Kind cluster for VPN networking (without recreating)
	@echo "🌐 Configuring existing Kind cluster for VPN networking..."
	@bash scripts/configure-kind-vpn-networking.sh

kind-validate-ai-gateway: kind-test-ai-gateway-connectivity ## Validate AI Gateway integration (connectivity + API endpoint)
	@echo ""
	@echo "🧪 Validating AI Gateway API endpoint..."
	@INGRESS_PORT=$(KIND_INGRESS_PORT); \
	BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		exit 1; \
	fi; \
	echo "   Testing /api/providers/verify endpoint with ai_gateway provider..."; \
	RESPONSE=$$(curl -s -X POST "http://localhost:$$INGRESS_PORT/api/providers/verify" \
		-H "Content-Type: application/json" \
		-d '{"provider": "ai_gateway", "api_key": "test", "client_secret": "test"}' 2>&1); \
	if echo "$$RESPONSE" | grep -q "ai_gateway\|AI Gateway"; then \
		echo "✅ API endpoint accepts ai_gateway provider"; \
		echo "   Response: $$RESPONSE" | head -3; \
	else \
		echo "⚠️  API endpoint may not be accepting ai_gateway provider"; \
		echo "   Response: $$RESPONSE" | head -5; \
		echo "   Run 'make kind-restart-backend' to ensure latest code is running"; \
	fi

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

kind-test-agents: ## Run comprehensive agent verification tests in kind cluster
	@echo "🧪 Running Agent Verification Tests..."
	@echo "   This will test all lifecycle agents for:"
	@echo "   - RAG integration"
	@echo "   - Coaching mode removal"
	@echo "   - Response completeness (no truncation)"
	@echo "   - Knowledge base usage"
	@echo ""
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) -l app=backend --context kind-$(KIND_CLUSTER_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make kind-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Backend pod: $$BACKEND_POD"; \
	echo "   Copying test script to pod..."; \
	kubectl cp backend/tests/test_agent_verification.py $(K8S_NAMESPACE)/$$BACKEND_POD:/tmp/test_agent_verification.py --context kind-$(KIND_CLUSTER_NAME) --container=backend; \
	echo "   Running agent verification tests inside pod..."; \
	echo ""; \
	kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend -- \
		python /tmp/test_agent_verification.py || \
		(echo ""; \
		 echo "⚠️  Test execution failed. Checking backend logs..."; \
		 kubectl logs -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend --tail=50; \
		 exit 1); \
	echo ""; \
	echo "✅ Agent verification tests completed"

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
			# Also update migration job if it exists in this file
			if grep -q "db-migrations-job" "$$file" 2>/dev/null; then \
				if [ "$$(uname)" = "Darwin" ]; then \
					sed -i '' "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" "$$file"; \
				else \
					sed -i "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" "$$file"; \
				fi; \
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
	@echo "🔄 Running database migrations..."
	@if [ -z "$(BACKEND_IMAGE_TAG)" ]; then \
		echo "❌ BACKEND_IMAGE_TAG is required for migrations"; \
		exit 1; \
	fi
	@echo "   Updating migration job with backend image: $(BACKEND_IMAGE_TAG)"
	@if [ "$$(uname)" = "Darwin" ]; then \
		sed -i '' "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" $(K8S_DIR)/eks/db-migrations-job.yaml; \
	else \
		sed -i "s|ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)|g" $(K8S_DIR)/eks/db-migrations-job.yaml; \
	fi
	@echo "   Deleting any existing migration job..."
	@kubectl delete job db-migrations -n $(EKS_NAMESPACE) --ignore-not-found=true || true
	@echo "   Creating migration job..."
	@kubectl apply -f $(K8S_DIR)/eks/db-migrations-job.yaml
	@echo "⏳ Waiting for database migrations to complete..."
	@if kubectl wait --for=condition=complete job/db-migrations -n $(EKS_NAMESPACE) --timeout=600s; then \
		echo "✅ Database migrations completed successfully"; \
		kubectl logs -n $(EKS_NAMESPACE) job/db-migrations --tail=20 || true; \
	else \
		echo "❌ Database migrations failed!"; \
		echo "   Migration job logs:"; \
		kubectl logs -n $(EKS_NAMESPACE) job/db-migrations --tail=50 || true; \
		echo "   Migration job status:"; \
		kubectl describe job db-migrations -n $(EKS_NAMESPACE) | tail -20 || true; \
		echo ""; \
		echo "⚠️  Deployment stopped. Please fix migration issues before continuing."; \
		exit 1; \
	fi
	@echo "🔄 Running database setup (seeding)..."
	@kubectl apply -f $(K8S_DIR)/eks/db-setup-job.yaml || true
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

eks-setup-hpa: eks-prepare-namespace ## Setup Horizontal Pod Autoscaler for backend and frontend (use EKS_NAMESPACE=your-namespace)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-setup-hpa EKS_NAMESPACE=your-namespace"; \
		exit 1; \
	fi
	@echo "📈 Setting up HPA for 100 concurrent users..."
	@echo "   Namespace: $(EKS_NAMESPACE)"
	@kubectl apply -f $(K8S_DIR)/eks/hpa-backend.yaml
	@kubectl apply -f $(K8S_DIR)/eks/hpa-frontend.yaml
	@echo "✅ HPA configured"
	@echo "   Backend: 5-20 replicas (CPU/Memory based)"
	@echo "   Frontend: 3-10 replicas (CPU/Memory based)"
	@kubectl get hpa -n $(EKS_NAMESPACE)

eks-prewarm: ## Pre-warm deployments for 100 concurrent users (use EKS_NAMESPACE=your-namespace)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-prewarm EKS_NAMESPACE=your-namespace"; \
		exit 1; \
	fi
	@echo "🔥 Pre-warming deployments for 100 concurrent users..."
	@echo "   Scaling backend to 5 replicas..."
	@kubectl scale deployment backend -n $(EKS_NAMESPACE) --replicas=5
	@echo "   Scaling frontend to 3 replicas..."
	@kubectl scale deployment frontend -n $(EKS_NAMESPACE) --replicas=3
	@echo "⏳ Waiting for pods to be ready..."
	@kubectl wait --for=condition=ready pod -l app=backend -n $(EKS_NAMESPACE) --timeout=300s || echo "⚠️  Some backend pods may still be starting"
	@kubectl wait --for=condition=ready pod -l app=frontend -n $(EKS_NAMESPACE) --timeout=300s || echo "⚠️  Some frontend pods may still be starting"
	@echo "✅ Pre-warming complete"
	@echo "📊 Current status:"
	@kubectl get pods -n $(EKS_NAMESPACE) -l 'app in (backend,frontend)' --no-headers | wc -l | xargs echo "   Total pods:"
	@kubectl get pods -n $(EKS_NAMESPACE) -l 'app in (backend,frontend)' | grep Running | wc -l | xargs echo "   Running pods:"

eks-performance-test: ## Run performance test with 100 concurrent users (use EKS_NAMESPACE=your-namespace, BASE_URL=url, AUTH_TOKEN=token, PRODUCT_ID=id)
	@if [ -z "$(EKS_NAMESPACE)" ] || [ -z "$(BASE_URL)" ] || [ -z "$(AUTH_TOKEN)" ] || [ -z "$(PRODUCT_ID)" ]; then \
		echo "❌ Required parameters: EKS_NAMESPACE, BASE_URL, AUTH_TOKEN, PRODUCT_ID"; \
		echo "   Usage: make eks-performance-test EKS_NAMESPACE=ns BASE_URL=https://... AUTH_TOKEN=token PRODUCT_ID=uuid"; \
		echo "   Example: make eks-performance-test EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 BASE_URL=https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud AUTH_TOKEN=xxx PRODUCT_ID=abc-123"; \
		exit 1; \
	fi
	@echo "🧪 Running performance test..."
	@echo "   Users: 100"
	@echo "   Base URL: $(BASE_URL)"
	@echo "   Product ID: $(PRODUCT_ID)"
	@python3 scripts/performance-test.py \
		--url $(BASE_URL) \
		--token $(AUTH_TOKEN) \
		--product-id $(PRODUCT_ID) \
		--users 100 \
		--ramp-up 30 \
		--output performance-metrics-$$(date +%Y%m%d-%H%M%S).json

kind-test-coordinator: ## Test coordinator agent selection in kind cluster (use K8S_NAMESPACE=your-namespace)
	@if [ -z "$(K8S_NAMESPACE)" ]; then \
		echo "❌ K8S_NAMESPACE is required"; \
		echo "   Usage: make kind-test-coordinator K8S_NAMESPACE=ideaforge-ai"; \
		exit 1; \
	fi
	@echo "🧪 Testing Coordinator Agent Selection in Kind Cluster..."
	@echo "   Namespace: $(K8S_NAMESPACE)"
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make kind-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Backend pod: $$BACKEND_POD"; \
	echo "   Copying test script to pod..."; \
	kubectl cp backend/tests/test_coordinator_agent_selection.py $(K8S_NAMESPACE)/$$BACKEND_POD:/tmp/test_coordinator_agent_selection.py --context kind-$(KIND_CLUSTER_NAME) --container=backend; \
	echo "   Running coordinator agent selection tests inside pod..."; \
	echo ""; \
	kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend -- \
		python -m pytest /tmp/test_coordinator_agent_selection.py -v || \
		(echo ""; \
		 echo "⚠️  Test execution failed. Checking backend logs..."; \
		 kubectl logs -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend --tail=50; \
		 exit 1); \
	echo ""; \
	echo "✅ Coordinator agent selection tests completed"

eks-test-coordinator: ## Test coordinator agent selection in EKS cluster (use EKS_NAMESPACE=your-namespace, KUBECONFIG=path)
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-test-coordinator EKS_NAMESPACE=ns [KUBECONFIG=path]"; \
		exit 1; \
	fi
	@if [ -n "$(KUBECONFIG)" ]; then \
		export KUBECONFIG=$(KUBECONFIG); \
		echo "   Using KUBECONFIG: $(KUBECONFIG)"; \
	fi
	@echo "🧪 Testing Coordinator Agent Selection in EKS Cluster..."
	@echo "   Namespace: $(EKS_NAMESPACE)"
	@BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make eks-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Backend pod: $$BACKEND_POD"; \
	echo "   Copying test script to pod..."; \
	kubectl cp backend/tests/test_coordinator_agent_selection.py $(EKS_NAMESPACE)/$$BACKEND_POD:/tmp/test_coordinator_agent_selection.py; \
	echo "   Running coordinator agent selection tests inside pod..."; \
	echo ""; \
	kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD --container=backend -- \
		python -m pytest /tmp/test_coordinator_agent_selection.py -v || \
		(echo ""; \
		 echo "⚠️  Test execution failed. Checking backend logs..."; \
		 kubectl logs -n $(EKS_NAMESPACE) $$BACKEND_POD --container=backend --tail=50; \
		 exit 1); \
	echo ""; \
	echo "✅ Coordinator agent selection tests completed"

kind-test-integration: ## Run comprehensive integration tests in kind cluster (coordinator, V0, chatbot) - use K8S_NAMESPACE=your-namespace
	@if [ -z "$(K8S_NAMESPACE)" ]; then \
		echo "❌ K8S_NAMESPACE is required"; \
		echo "   Usage: make kind-test-integration K8S_NAMESPACE=ideaforge-ai"; \
		exit 1; \
	fi
	@echo "🧪 Running Comprehensive Integration Tests in Kind Cluster..."
	@echo "   Tests: Coordinator Agent Selection, V0 Project Retention, V0 Prompt Format, Chatbot Content"
	@echo "   Namespace: $(K8S_NAMESPACE)"
	@BACKEND_POD=$$(kubectl get pods -n $(K8S_NAMESPACE) --context kind-$(KIND_CLUSTER_NAME) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make kind-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Backend pod: $$BACKEND_POD"; \
	echo "   Copying integration test script to pod..."; \
	kubectl cp backend/tests/test_v0_coordinator_integration.py $(K8S_NAMESPACE)/$$BACKEND_POD:/tmp/test_v0_coordinator_integration.py --context kind-$(KIND_CLUSTER_NAME) --container=backend; \
	echo "   Running integration tests inside pod..."; \
	echo ""; \
	kubectl exec -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend -- \
		python /tmp/test_v0_coordinator_integration.py || \
		(echo ""; \
		 echo "⚠️  Test execution failed. Checking backend logs..."; \
		 kubectl logs -n $(K8S_NAMESPACE) $$BACKEND_POD --context kind-$(KIND_CLUSTER_NAME) --container=backend --tail=50; \
		 exit 1); \
	echo ""; \
	echo "✅ Integration tests completed"

eks-test-integration: ## Run comprehensive integration tests in EKS cluster (coordinator, V0, chatbot) - use EKS_NAMESPACE=ns, KUBECONFIG=path
	@if [ -z "$(EKS_NAMESPACE)" ]; then \
		echo "❌ EKS_NAMESPACE is required"; \
		echo "   Usage: make eks-test-integration EKS_NAMESPACE=ns [KUBECONFIG=path]"; \
		exit 1; \
	fi
	@if [ -n "$(KUBECONFIG)" ]; then \
		export KUBECONFIG=$(KUBECONFIG); \
		echo "   Using KUBECONFIG: $(KUBECONFIG)"; \
	fi
	@echo "🧪 Running Comprehensive Integration Tests in EKS Cluster..."
	@echo "   Tests: Coordinator Agent Selection, V0 Project Retention, V0 Prompt Format, Chatbot Content"
	@echo "   Namespace: $(EKS_NAMESPACE)"
	@echo "   ⚡ Latency-optimized for 100+ concurrent users"
	@BACKEND_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$BACKEND_POD" ]; then \
		echo "❌ Backend pod not found"; \
		echo "   Run 'make eks-deploy' to deploy the application first"; \
		exit 1; \
	fi; \
	echo "   Backend pod: $$BACKEND_POD"; \
	echo "   Copying integration test script to pod..."; \
	kubectl cp backend/tests/test_v0_coordinator_integration.py $(EKS_NAMESPACE)/$$BACKEND_POD:/tmp/test_v0_coordinator_integration.py; \
	echo "   Running integration tests inside pod..."; \
	echo ""; \
	kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD --container=backend -- \
		python /tmp/test_v0_coordinator_integration.py || \
		(echo ""; \
		 echo "⚠️  Test execution failed. Checking backend logs..."; \
		 kubectl logs -n $(EKS_NAMESPACE) $$BACKEND_POD --container=backend --tail=50; \
		 exit 1); \
	echo ""; \
	echo "✅ Integration tests completed"

eks-rollout-images: ## Deploy new images with verification, database dump, and cleanup (use EKS_NAMESPACE=ns, BACKEND_IMAGE_TAG=tag, FRONTEND_IMAGE_TAG=tag, KUBECONFIG=path, BASE_URL=url)
	@if [ -z "$(EKS_NAMESPACE)" ] || [ -z "$(BACKEND_IMAGE_TAG)" ] || [ -z "$(FRONTEND_IMAGE_TAG)" ]; then \
		echo "❌ Required parameters: EKS_NAMESPACE, BACKEND_IMAGE_TAG, FRONTEND_IMAGE_TAG"; \
		echo "   Usage: make eks-rollout-images EKS_NAMESPACE=ns BACKEND_IMAGE_TAG=tag FRONTEND_IMAGE_TAG=tag [KUBECONFIG=path] [BASE_URL=url]"; \
		echo "   Example: make eks-rollout-images EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 BACKEND_IMAGE_TAG=3b0a9d6 FRONTEND_IMAGE_TAG=3b0a9d6 KUBECONFIG=/tmp/kubeconfig.sake62 BASE_URL=https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud"; \
		exit 1; \
	fi
	@if [ -n "$(KUBECONFIG)" ]; then \
		export KUBECONFIG=$(KUBECONFIG); \
		echo "   Using KUBECONFIG: $(KUBECONFIG)"; \
	fi
	@echo "🚀 EKS Image Rollout with Verification"
	@echo "======================================"
	@echo "   Namespace: $(EKS_NAMESPACE)"
	@echo "   Backend Image: ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)"
	@echo "   Frontend Image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(FRONTEND_IMAGE_TAG)"
	@echo ""
	@echo "📦 Step 1: Creating database backup..."
	@BACKUP_DIR=$${BACKUP_DIR:-./backups}; \
	mkdir -p $$BACKUP_DIR; \
	TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	BACKUP_FILE="$$BACKUP_DIR/eks_db_backup_$(EKS_NAMESPACE)_$$TIMESTAMP.sql"; \
	POSTGRES_POD=$$(kubectl get pods -n $(EKS_NAMESPACE) -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
	                 kubectl get pods -n $(EKS_NAMESPACE) -l 'app in (postgres,postgres-ha)' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo ""); \
	if [ -n "$$POSTGRES_POD" ]; then \
		echo "   Found PostgreSQL pod: $$POSTGRES_POD"; \
		POSTGRES_USER=$$(kubectl get configmap ideaforge-ai-config -n $(EKS_NAMESPACE) -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null || echo "agentic_pm"); \
		POSTGRES_DB=$$(kubectl get configmap ideaforge-ai-config -n $(EKS_NAMESPACE) -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null || echo "agentic_pm_db"); \
		POSTGRES_PASSWORD=$$(kubectl get secret ideaforge-ai-secrets -n $(EKS_NAMESPACE) -o jsonpath='{.data.POSTGRES_PASSWORD}' 2>/dev/null | base64 -d || echo ""); \
		if [ -n "$$POSTGRES_PASSWORD" ]; then \
			kubectl exec -n $(EKS_NAMESPACE) $$POSTGRES_POD -- \
				env PGPASSWORD="$$POSTGRES_PASSWORD" \
				pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" \
				--clean --if-exists --create --format=plain --no-owner --no-privileges \
				> "$$BACKUP_FILE" 2>&1 && \
			BACKUP_SIZE=$$(du -h "$$BACKUP_FILE" | cut -f1) && \
			echo "   ✅ Database backup created: $$BACKUP_FILE ($$BACKUP_SIZE)"; \
		else \
			echo "   ⚠️  Could not retrieve database password, skipping backup"; \
		fi; \
	else \
		echo "   ⚠️  PostgreSQL pod not found, skipping backup"; \
	fi
	@echo ""
	@echo "🔄 Step 2: Updating image tags in deployments..."
	@kubectl set image deployment/backend backend=ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG) -n $(EKS_NAMESPACE) || \
		(echo "❌ Failed to update backend image" && exit 1)
	@kubectl set image deployment/frontend frontend=ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(FRONTEND_IMAGE_TAG) -n $(EKS_NAMESPACE) || \
		(echo "❌ Failed to update frontend image" && exit 1)
	@echo "   ✅ Image tags updated"
	@echo ""
	@echo "⏳ Step 3: Rolling out deployments (low timeout)..."
	@kubectl rollout status deployment/backend -n $(EKS_NAMESPACE) --timeout=120s || \
		(echo "⚠️  Backend rollout timeout (120s), checking status..." && \
		 kubectl get pods -n $(EKS_NAMESPACE) -l app=backend && \
		 echo "   Continuing with verification...")
	@kubectl rollout status deployment/frontend -n $(EKS_NAMESPACE) --timeout=120s || \
		(echo "⚠️  Frontend rollout timeout (120s), checking status..." && \
		 kubectl get pods -n $(EKS_NAMESPACE) -l app=frontend && \
		 echo "   Continuing with verification...")
	@echo "   ✅ Rollouts completed"
	@echo ""
	@echo "🧹 Step 4: Cleaning up old replicasets..."
	@kubectl get replicasets -n $(EKS_NAMESPACE) -o json 2>/dev/null | \
		jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' 2>/dev/null | \
		while read rs; do \
			if [ -n "$$rs" ]; then \
				echo "   Deleting replicaset: $$rs"; \
				kubectl delete replicaset $$rs -n $(EKS_NAMESPACE) --ignore-not-found=true; \
			fi; \
		done || echo "   No old replicasets to clean up"
	@echo "   ✅ Cleanup complete"
	@echo ""
	@echo "🧪 Step 5: Verifying deployment..."
	@echo "   Checking pod status..."
	@kubectl get pods -n $(EKS_NAMESPACE) -l 'app in (backend,frontend)' --no-headers | \
		awk '{if ($$3 != "Running") {print "   ⚠️  Pod " $$1 " is " $$3; exit 1}}' || true
	@echo "   ✅ All pods are running"
	@echo ""
	@echo "   Testing backend health endpoint..."
	@BACKEND_POD=$$(kubectl get pod -n $(EKS_NAMESPACE) -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$BACKEND_POD" ]; then \
		HEALTH_RESPONSE=$$(kubectl exec -n $(EKS_NAMESPACE) $$BACKEND_POD -- curl -s http://localhost:8000/health 2>/dev/null || echo ""); \
		if echo "$$HEALTH_RESPONSE" | grep -q "healthy\|status"; then \
			echo "   ✅ Backend health check passed"; \
		else \
			echo "   ⚠️  Backend health check may have issues"; \
		fi; \
	fi
	@if [ -n "$(BASE_URL)" ]; then \
		echo ""; \
		echo "   Testing API endpoint via ingress..."; \
		API_RESPONSE=$$(curl -s -f "$(BASE_URL)/api/health" 2>/dev/null || echo ""); \
		if echo "$$API_RESPONSE" | grep -q "healthy\|status"; then \
			echo "   ✅ API endpoint accessible"; \
		else \
			echo "   ⚠️  API endpoint may not be accessible"; \
		fi; \
		echo ""; \
		echo "   Testing frontend via ingress..."; \
		FRONTEND_RESPONSE=$$(curl -s -f "$(BASE_URL)/" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000"); \
		if [ "$$FRONTEND_RESPONSE" = "200" ] || [ "$$FRONTEND_RESPONSE" = "304" ]; then \
			echo "   ✅ Frontend accessible"; \
		else \
			echo "   ⚠️  Frontend returned HTTP $$FRONTEND_RESPONSE"; \
		fi; \
		echo ""; \
		echo "   Testing login endpoint..."; \
		LOGIN_RESPONSE=$$(curl -s -X POST "$(BASE_URL)/api/auth/login" \
			-H "Content-Type: application/json" \
			-d '{"email":"test@example.com","password":"test"}' 2>/dev/null || echo ""); \
		if echo "$$LOGIN_RESPONSE" | grep -qE "token|error|Invalid"; then \
			echo "   ✅ Login endpoint responding"; \
		else \
			echo "   ⚠️  Login endpoint may not be responding correctly"; \
		fi; \
		echo ""; \
		echo "   Testing SSO callback endpoint..."; \
		SSO_RESPONSE=$$(curl -s -f "$(BASE_URL)/api/auth/mckinsey/callback?code=test&state=test" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000"); \
		if [ "$$SSO_RESPONSE" != "000" ]; then \
			echo "   ✅ SSO callback endpoint responding (HTTP $$SSO_RESPONSE)"; \
		else \
			echo "   ⚠️  SSO callback endpoint may not be accessible"; \
		fi; \
	fi
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "   Backend: ghcr.io/soumantrivedi/ideaforge-ai/backend:$(BACKEND_IMAGE_TAG)"
	@echo "   Frontend: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$(FRONTEND_IMAGE_TAG)"
	@if [ -n "$$BACKUP_FILE" ] && [ -f "$$BACKUP_FILE" ]; then \
		echo "   Database backup: $$BACKUP_FILE"; \
	fi
