# Local Development Guide

Complete step-by-step guide for setting up and running IdeaForge AI locally using Kind cluster.

## Prerequisites

### Required Software

1. **Docker Desktop** (20.10+)
   - Download: https://www.docker.com/products/docker-desktop
   - Ensure Docker is running: `docker info`

2. **GNU Make**
   - macOS/Linux: Usually pre-installed
   - Windows: Use WSL2 or install via package manager

3. **kubectl** (for Kind cluster)
   - Install: https://kubernetes.io/docs/tasks/tools/
   - Verify: `kubectl version --client`

4. **kind** (Kubernetes in Docker)
   - Install: `brew install kind` (macOS) or follow https://kind.sigs.k8s.io/docs/user/quick-start/
   - Verify: `kind version`

5. **Git**
   - Verify: `git --version`

### API Keys (At Least One Required)

- OpenAI API Key: https://platform.openai.com/api-keys
- Anthropic Claude API Key: https://console.anthropic.com/
- Google Gemini API Key: https://makersuite.google.com/app/apikey
- V0 API Key (optional, for design prototypes): https://v0.app/chat/settings/api
- GitHub Token (optional, for integrations): https://github.com/settings/tokens

## Kind Cluster Setup

Kind cluster provides a production-like Kubernetes environment locally, making it ideal for testing Kubernetes deployments and matching production EKS setup.

### Step 1: Clone Repository

```bash
git clone <repository-url> ideaforge-ai
cd ideaforge-ai
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp env.kind.example env.kind

# Edit env.kind with your API keys
# Required: At least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
# Optional: V0_API_KEY, GITHUB_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN
nano env.kind  # or use your preferred editor
```

**Minimum required variables:**
```bash
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
GOOGLE_API_KEY=...
```

### Step 3: Build Application Images

```bash
# Build backend and frontend images
make build-apps
```

This creates:
- `ideaforge-ai-backend:<git-sha>`
- `ideaforge-ai-frontend:<git-sha>`

### Step 4: Deploy to Kind Cluster

**Option A: Full Automated Deployment (Recommended)**

```bash
# This single command does everything:
# - Creates Kind cluster
# - Installs NGINX ingress
# - Builds images
# - Loads images into Kind
# - Deploys application
# - Sets up database
# - Initializes Agno framework
make kind-deploy-full
```

**Option B: Step-by-Step Deployment**

```bash
# 1. Create Kind cluster
make kind-create

# 2. Install NGINX ingress controller
make kind-setup-ingress

# 3. Build application images (if not already done)
make build-apps

# 4. Load images into Kind cluster
make kind-load-images

# 5. Load secrets from env.kind file
make kind-load-secrets

# 6. Deploy application
make kind-deploy

# 7. Initialize Agno framework
make kind-agno-init
```

### Step 5: Verify Deployment

```bash
# Check cluster status
make kind-status

# Test service connectivity
make kind-test

# Verify application access
make kind-verify-access
```

### Step 6: Access Application

The application is accessible via:

1. **Ingress (Primary Method)**
   ```bash
   # Get ingress port (usually 8080)
   docker ps --filter "name=ideaforge-ai-control-plane" --format "{{.Ports}}"
   
   # Access via:
   # Frontend: http://localhost:8080/
   # Backend API: http://localhost:8080/api/
   # Health: http://localhost:8080/health
   ```

2. **Port Forwarding (Alternative)**
   ```bash
   make kind-port-forward
   # Then access:
   # Frontend: http://localhost:3001
   # Backend: http://localhost:8000
   ```

3. **Host Headers (Advanced)**
   ```bash
   # Add to /etc/hosts (macOS/Linux) or C:\Windows\System32\drivers\etc\hosts (Windows)
   sudo sh -c 'echo "127.0.0.1 ideaforge.local api.ideaforge.local" >> /etc/hosts'
   
   # Then access:
   # Frontend: http://ideaforge.local:8080
   # Backend: http://api.ideaforge.local:8080
   ```

### Step 7: Configure API Keys in UI

1. Open http://localhost:8080/ (or your ingress port)
2. Navigate to **Settings**
3. Enter your API keys
4. Click **Verify Key** for each provider
5. Click **Save Configuration**

### Step 8: Test Application

```bash
# Test backend health
curl http://localhost:8080/health

# Test API endpoint
curl http://localhost:8080/api/health

# Test multi-agent processing
curl -X POST http://localhost:8080/api/multi-agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "query": "Generate ideas for a productivity app",
    "coordination_mode": "enhanced_collaborative"
  }'
```

### Common Operations

```bash
# View logs
make kind-logs

# Check status
make kind-status

# Rebuild and redeploy
make rebuild-and-deploy-kind

# Clean up (keeps cluster)
make kind-cleanup

# Delete cluster
make kind-delete
```

## Option 2: Docker Compose (Simpler, Faster Startup)

Docker Compose is simpler and faster for quick development, but doesn't match production Kubernetes environment.

### Step 1: Clone Repository

```bash
git clone <repository-url> ideaforge-ai
cd ideaforge-ai
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys
nano .env
```

### Step 3: Build and Start

```bash
# Build all images
make build

# Start all services
make up

# Wait for services to be ready
sleep 10

# Check health
make health
```

### Step 4: Setup Database

```bash
# Run migrations
make db-migrate

# Seed database (optional)
make db-seed

# Initialize Agno framework
make agno-init
```

### Step 5: Access Application

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Step 6: Configure API Keys

1. Open http://localhost:3001
2. Navigate to **Settings**
3. Enter and verify API keys
4. Save configuration

### Common Operations

```bash
# View logs
make logs SERVICE=backend
make logs-all

# Restart services
make restart

# Stop services (preserves data)
make down

# Rebuild and restart
make rebuild

# Database backup
make db-backup

# Database restore
make db-restore BACKUP=backups/backup_file.sql
```

## Troubleshooting

### Kind Cluster Issues

**Problem: Cluster creation fails**
```bash
# Check Docker is running
docker info

# Delete existing cluster and retry
make kind-delete
make kind-create
```

**Problem: Images not loading**
```bash
# Verify images exist
docker images | grep ideaforge-ai

# Rebuild images
make build-apps

# Reload images
make kind-load-images
```

**Problem: Pods not starting**
```bash
# Check pod status
kubectl get pods -n ideaforge-ai --context kind-ideaforge-ai

# Check pod logs
kubectl logs -n ideaforge-ai -l app=backend --context kind-ideaforge-ai

# Check events
kubectl describe pod -n ideaforge-ai <pod-name> --context kind-ideaforge-ai
```

**Problem: Database connection errors**
```bash
# Check PostgreSQL pod
kubectl get pods -n ideaforge-ai -l app=postgres --context kind-ideaforge-ai

# Check PostgreSQL logs
kubectl logs -n ideaforge-ai -l app=postgres --context kind-ideaforge-ai

# Restart database setup job
kubectl delete job db-setup -n ideaforge-ai --context kind-ideaforge-ai
kubectl apply -f k8s/db-setup-job.yaml --context kind-ideaforge-ai
```

### API Key Issues

**Problem: Keys show as invalid**
- Verify keys are correct in Settings
- Check network connectivity (corporate proxies may block)
- Verify API key has sufficient credits/quota
- Check backend logs for detailed error messages

**Problem: Agents not working**
- Ensure at least one API key is configured and verified
- Check provider status pages (OpenAI, Anthropic, Google)
- Verify backend logs for provider connection errors

## Next Steps

1. **Explore the UI**: Navigate through Product Lifecycle phases
2. **Test Multi-Agent System**: Try different coordination modes
3. **Review Architecture**: See `docs/architecture/01-high-level-architecture.md`
4. **Customize Agents**: Modify agents in `backend/agents/`
5. **Deploy to Production**: Follow `docs/guides/eks-production-guide.md`

## Additional Resources

- [Make Targets Reference](./make-targets.md)
- [Quick Start Guide](./quick-start.md)
- [Troubleshooting Guide](../troubleshooting/common-issues.md)
- [Database Migration Guide](./database-migration.md)
- [Multi-Agent System Guide](./multi-agent-system.md)

