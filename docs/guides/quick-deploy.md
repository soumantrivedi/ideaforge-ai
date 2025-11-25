# Quick Deployment Guide

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- At least 4GB RAM available
- 10GB disk space

## Quick Start

### 1. Clone and Navigate

```bash
cd ideaforge-ai
```

### 2. Create Environment File

Copy `.env.example` to `.env`. Minimum configuration:

```bash
# Optional overrides – the defaults already match docker-compose
DATABASE_URL=postgresql+asyncpg://agentic_pm:devpassword@postgres:5432/agentic_pm_db

# At least one provider key (also configurable through the UI)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Frontend builds read this
VITE_API_URL=http://localhost:8000
```

> 💡 You can leave the provider values empty here and supply them through the UI. The new Provider Registry lets you verify and persist keys at runtime.

### 3. Deploy Using Script

```bash
./deploy.sh
```

The script will:
- ✅ Check for required environment variables
- ✅ Verify Docker installation
- ✅ Build Docker images
- ✅ Start all services
- ✅ Perform health checks

### 4. Manual Deployment (Alternative)

If you prefer to deploy manually:

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Access the Application

Once deployed, access:

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Service Status

Check if services are running:

```bash
docker-compose ps
```

Expected output (ports may vary if you customised mapping):

```
NAME                       STATUS       PORTS
ideaforge-ai-backend-1     Up (healthy) 0.0.0.0:8000->8000/tcp
ideaforge-ai-frontend-1    Up           0.0.0.0:3001->3000/tcp
ideaforge-ai-redis-1       Up           0.0.0.0:6379->6379/tcp
ideaforge-ai-postgres-1    Up (healthy) 0.0.0.0:5433->5432/tcp
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs backend
docker-compose logs frontend

# Rebuild if needed
docker-compose build --no-cache
docker-compose up -d
```

### Backend Health Check Fails

```bash
# Check backend logs
docker-compose logs backend

# Test backend directly
curl http://localhost:8000/health

# Restart backend
docker-compose restart backend
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Verify environment variables
docker-compose exec frontend env | grep VITE_

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

### Port Already in Use

If ports 3001, 8000, 5433, or 6379 are already in use:

1. Stop conflicting services, or
2. Update port mappings in `docker-compose.yml`:
   ```yaml
   ports:
     - "3001:3000"  # Change frontend port
     - "8001:8000"  # Change backend port
   ```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

## Updating Services

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d

# Or use the deploy script
./deploy.sh
```

## Multi-Agent System

The backend now includes a comprehensive multi-agent system. Test it:

```bash
# Get agent capabilities
curl http://localhost:8000/api/agents/capabilities

# Test multi-agent request
curl -X POST http://localhost:8000/api/multi-agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000000",
    "query": "Analyze market opportunities for AI tools",
    "coordination_mode": "collaborative",
    "primary_agent": "research",
    "supporting_agents": ["analysis", "strategy"]
  }'
```

## Next Steps

1. **Verify provider keys** from the UI (Settings → Verify Key → Save Configuration).
2. **Test the application** at http://localhost:3001.
3. **Review documentation** under `docs/guides/` for architecture, lifecycle workflows, and production hardening.

## Production Deployment

### EKS Deployment

For EKS (Elastic Kubernetes Service) deployment:

```bash
# 1. Create namespace first (REQUIRED - deployment will NOT create it)
kubectl create namespace 20890-ideaforge-ai-dev-58a50

# 2. Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Deploy with specific image tags (recommended)
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=fab20a2 \
  FRONTEND_IMAGE_TAG=e1dc1da
```

**Important Notes**:
- The namespace **MUST exist** before deployment
- Use specific image tags (commit SHAs or versions) instead of `latest` for production
- See `k8s/EKS_DEPLOYMENT_GUIDE.md` for detailed EKS deployment guide
- See `k8s/EKS_IMAGE_TAGS.md` for image tag configuration details

### Docker Compose Production

For production deployment with Docker Compose, see `DEPLOYMENT_GUIDE.md` for:
- Security hardening
- SSL/HTTPS configuration
- Monitoring setup
- Scaling strategies
- Backup procedures

---

**Need Help?** Check the logs: `docker-compose logs -f`

