# Quick Start Guide

Everything you need to get IdeaForge AI running locally in under 10 minutes.

## 1. Prerequisites

- **Docker Desktop** 20.10+ (must be running)
- **GNU Make** (macOS/Linux include it; Windows users can run via WSL)
- **kubectl** and **kind** installed
- At least one API key (OpenAI, Anthropic Claude, or Google Gemini)

```bash
docker --version
kubectl version --client
kind version
```

## 2. Clone & Configure

```bash
git clone <repo> ideaforge-ai
cd ideaforge-ai

# Copy environment template for Kind cluster
cp env.kind.example env.kind

# Edit env.kind with your API keys (at least one required)
nano env.kind  # or use your preferred editor
```

**Required Environment Variables:**
- At least one of: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- Optional: `V0_API_KEY`, `GITHUB_TOKEN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `ATLASSIAN_CLOUD_ID`

**Important:** The `kind-load-secrets` make target automatically loads all variables from `env.kind` (or `.env` if `env.kind` doesn't exist) into Kubernetes secrets. This ensures all API keys and configuration are available to the application.

## 3. Build & Deploy

### Option A: Full Automated Deployment (Recommended)

```bash
# Build application images
make build-apps

# Complete deployment (creates cluster, installs ingress, loads secrets, deploys, runs migrations)
make kind-deploy-full
```

This single command handles everything:
1. ✅ Creates Kind cluster
2. ✅ Sets up NGINX ingress controller
3. ✅ Builds Docker images
4. ✅ Loads images into Kind cluster
5. ✅ **Loads secrets from env.kind file** (via `kind-load-secrets`)
6. ✅ Creates ConfigMaps for database migrations
7. ✅ Deploys all services
8. ✅ **Runs database migrations** (via `db-setup` job)
9. ✅ Seeds database with demo accounts
10. ✅ Initializes Agno framework
11. ✅ Verifies access

### Option B: Step-by-Step Deployment

```bash
# 1. Build images
make build-apps

# 2. Create Kind cluster
make kind-create

# 3. Setup ingress
make kind-setup-ingress

# 4. Load images into cluster
make kind-load-images

# 5. Load secrets from env.kind (REQUIRED for API keys and configuration)
make kind-load-secrets

# 6. Deploy application (includes DB migrations and seeding)
make kind-deploy-internal
```

**Services:**
- Frontend: http://localhost:8080/ (or check ingress port with `make kind-show-access-info`)
- Backend API: http://localhost:8080/api/
- API docs: http://localhost:8080/api/docs
- Health: http://localhost:8080/health

## 4. Verify Deployment

```bash
# Check pod status
make kind-status

# Check logs for errors
make kind-logs

# Verify all services are running
kubectl get pods -n ideaforge-ai --context kind-ideaforge-ai

# Verify secrets are loaded
kubectl get secret ideaforge-ai-secrets -n ideaforge-ai --context kind-ideaforge-ai
```

## 5. Configure & Verify API Keys

1. Open the UI at **http://localhost:8080/** → **Settings**.
2. Enter one or more provider keys (or they're already loaded from `env.kind` via `kind-load-secrets`).
3. Use the **Verify Key** button to test each key.
4. Click **Save Configuration** to register keys with the backend.

👉 **Note:** If you used `make kind-load-secrets`, API keys are already loaded into Kubernetes secrets and available to the backend. The UI allows you to verify and manage them.

## 6. First Interactions

### Test an agent
```bash
curl -X POST http://localhost:8080/api/multi-agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "Generate feature ideas for a team productivity app",
    "primary_agent": "ideation",
    "product_id": "<product-id>"
  }'
```

### Run the multi-agent workflow
```bash
curl -X POST http://localhost:8080/api/multi-agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "Create a PRD outline for an AI onboarding copilot",
    "coordination_mode": "collaborative",
    "primary_agent": "ideation",
    "supporting_agents": ["research", "analysis", "strategy"]
  }'
```

Then switch back to the UI and iterate via the Product Lifecycle wizard.

## 7. Helpful Commands

```bash
make kind-status          # Show cluster status
make kind-logs            # Show logs from all pods
make kind-verify-access   # Verify application is accessible
make kind-show-access-info # Show access URLs and information
make kind-restart         # Restart all deployments
make kind-cleanup         # Clean up deployment (keeps cluster)
make kind-delete          # Delete the entire cluster
```

## 8. Troubleshooting

| Symptom | Try This |
|---------|----------|
| Pods not starting | Check `kubectl get pods -n ideaforge-ai --context kind-ideaforge-ai` and `kubectl describe pod <pod-name>` |
| "Secrets not found" | Run `make kind-load-secrets` to load secrets from `env.kind` |
| Database migration errors | Check `kubectl logs -n ideaforge-ai job/db-setup --context kind-ideaforge-ai` |
| Agno agents not initialized | Verify API keys are loaded: `kubectl get secret ideaforge-ai-secrets -n ideaforge-ai --context kind-ideaforge-ai` |
| "Connection error" from agents | Ensure API keys are valid and loaded via `make kind-load-secrets` |
| Ports already in use | Check ingress port: `kubectl get ingress -n ideaforge-ai --context kind-ideaforge-ai` |
| Database connection errors | Verify PostgreSQL pod is running: `kubectl get pods -n ideaforge-ai -l app=postgres --context kind-ideaforge-ai` |

## 9. Production Deployment (EKS)

For production deployment to EKS:

```bash
# 1. Setup environment
cp env.eks.example env.eks
# Edit env.eks with production configuration

# 2. Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Create namespace (REQUIRED - must exist before deployment)
kubectl create namespace <your-namespace>

# 4. Full deployment (handles secrets, migrations, everything)
make eks-deploy-full \
  EKS_NAMESPACE=<your-namespace> \
  BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD) \
  FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)
```

The `eks-deploy-full` target handles:
- ✅ GHCR secret setup (for pulling images)
- ✅ Namespace preparation
- ✅ **Secrets loading** (via `eks-load-secrets` from `env.eks`)
- ✅ **Database migrations** (via `db-setup` job)
- ✅ Full deployment
- ✅ Agno framework initialization

## 10. Next Steps

1. Review [Local Development Guide](local-development-guide.md) for detailed setup.
2. Review [EKS Production Deployment Guide](../deployment/PRODUCTION_DEPLOYMENT_GUIDE.md) for production setup.
3. Explore [Multi-Agent System](multi-agent-system.md) to understand agent collaboration.
4. Review [Product Lifecycle](product-lifecycle.md) for lifecycle management.
5. Customize or extend agents in `backend/agents/`.

Happy building! 🎉
