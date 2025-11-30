# IdeaForgeAI-v2 Deployment Instructions

## Prerequisites

1. **Docker Desktop must be running**
   ```bash
   # Check if Docker is running
   docker info
   
   # If not running, start Docker Desktop manually
   # On macOS: Open Docker Desktop application
   ```

2. **Ports must be available**
   - Port `8081` (frontend)
   - Port `8443` (HTTPS ingress)
   - If ports are in use, kill the processes:
     ```bash
     lsof -ti:8081 | xargs kill -9
     lsof -ti:8443 | xargs kill -9
     ```

## Deployment Steps

### Step 1: Start Docker Desktop
Ensure Docker Desktop is running before proceeding.

### Step 2: Deploy to Kind Cluster

```bash
cd /Users/Souman_Trivedi/IdeaProjects/ideaForgeAI-v2

# Set environment variables
export KIND_CLUSTER_NAME=ideaforge-ai
export K8S_NAMESPACE=ideaforge-ai
export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")

# Complete deployment (one command)
make kind-deploy-full KIND_CLUSTER_NAME=$KIND_CLUSTER_NAME K8S_NAMESPACE=$K8S_NAMESPACE
```

This will:
1. Create Kind cluster
2. Setup ingress controller
3. Build Docker images
4. Load images into cluster
5. Load secrets
6. Deploy all services
7. Setup and seed database
8. Verify access

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -n ideaforge-ai

# Check services
kubectl get svc -n ideaforge-ai

# Check ingress
kubectl get ingress -n ideaforge-ai

# View logs
kubectl logs -n ideaforge-ai -l app=backend --tail=50
```

### Step 4: Access Application

**Frontend:** http://localhost:8081

**Backend API:** http://localhost:8081/api

### Step 5: Port Forwarding (Alternative Access)

If ingress doesn't work, use port forwarding:

```bash
# Frontend
kubectl port-forward -n ideaforge-ai svc/frontend 8081:80

# Backend (in another terminal)
kubectl port-forward -n ideaforge-ai svc/backend 8000:8000
```

## Performance Validation

### Test 1: Single Agent Query
```bash
curl -X POST http://localhost:8081/api/multi-agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "What is a good product idea?", "product_id": "test"}'
```

**Expected:** Response time < 10 seconds

### Test 2: Multi-Agent Parallel Query
```bash
curl -X POST http://localhost:8081/api/multi-agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "Research market trends and analyze competitors for a fitness app",
    "product_id": "test",
    "coordination_mode": "parallel"
  }'
```

**Expected:** Response time < 45 seconds

### Test 3: Verify Model Tiers
```bash
kubectl logs -n ideaforge-ai -l app=backend | grep -i "model_tier\|fast\|standard"
```

**Expected:** See model tier assignments in logs

### Test 4: Verify Metrics
```bash
kubectl logs -n ideaforge-ai -l app=backend | grep -i "agent_metrics\|total_calls\|avg_time"
```

**Expected:** See metrics logged for agent calls

## Troubleshooting

### Docker Not Running
```bash
# Start Docker Desktop manually
open -a Docker
# Wait 30 seconds for Docker to start
sleep 30
docker info
```

### Port Conflicts
```bash
# Find and kill processes using ports
lsof -ti:8081 | xargs kill -9
lsof -ti:8443 | xargs kill -9
```

### Cluster Creation Fails
```bash
# Delete existing cluster
make kind-delete KIND_CLUSTER_NAME=ideaforge-ai

# Try again
make kind-create KIND_CLUSTER_NAME=ideaforge-ai
```

### Pods Not Starting
```bash
# Check pod status
kubectl describe pod -n ideaforge-ai <pod-name>

# Check logs
kubectl logs -n ideaforge-ai <pod-name>
```

### Frontend Build Fails
```bash
cd src
rm -rf node_modules
npm install
npm run build
```

## Quick Deployment Script

Save this as `deploy-v2.sh`:

```bash
#!/bin/bash
set -e

export KIND_CLUSTER_NAME=ideaforge-ai
export K8S_NAMESPACE=ideaforge-ai
export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")

echo "🚀 Deploying IdeaForgeAI-v2..."
echo "Cluster: $KIND_CLUSTER_NAME"
echo "Namespace: $K8S_NAMESPACE"
echo "Git SHA: $GIT_SHA"
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Deploy
make kind-deploy-full KIND_CLUSTER_NAME=$KIND_CLUSTER_NAME K8S_NAMESPACE=$K8S_NAMESPACE

echo ""
echo "✅ Deployment complete!"
echo "Frontend: http://localhost:8081"
echo "Backend: http://localhost:8081/api"
```

Make it executable and run:
```bash
chmod +x deploy-v2.sh
./deploy-v2.sh
```
