# Production Deployment Guide - EKS

This guide covers the complete production deployment process for IdeaForge AI on EKS, including database backup, migrations, secrets management, and verification.

## Prerequisites

1. **AWS EKS Cluster** configured and accessible via kubectl
2. **Docker images** built and pushed to container registry (GHCR or ECR)
3. **.env file** with all required secrets and API keys
4. **kubectl** configured with access to EKS cluster

## Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] Database backup script ready
- [ ] All API keys configured in .env file
- [ ] Docker images built and tagged
- [ ] kubectl context set to EKS cluster
- [ ] Namespace exists or will be created

### 2. Database Backup (Before Upgrade)

**Important**: Always backup the database before running migrations in production.

```bash
# Manual backup
kubectl exec -n <NAMESPACE> <POSTGRES_POD> -- pg_dump -U agentic_pm -d agentic_pm_db \
  --clean --if-exists --create \
  --format=plain \
  --no-owner --no-privileges \
  > backups/eks_db_backup_<NAMESPACE>_<TIMESTAMP>.sql
```

The deployment script automatically creates backups before migrations.

### 3. Load Secrets and ConfigMaps

#### Option A: Using .env file (Recommended)

```bash
# Load secrets from .env file (uses make target)
make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>

# Apply ConfigMaps (handled by make eks-deploy-full)
# Or manually: kubectl apply -f k8s/eks/configmap.yaml -n <NAMESPACE>
```

#### Option B: Manual Secret Creation

```bash
kubectl create secret generic ideaforge-ai-secrets \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  --from-literal=GOOGLE_API_KEY=your-key \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --from-literal=SESSION_SECRET=your-secret \
  --from-literal=API_KEY_ENCRYPTION_KEY=your-key \
  -n <NAMESPACE> \
  --dry-run=client -o yaml | kubectl apply -f -
```

**Required Secrets:**
- `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY` - at least one)
- `POSTGRES_PASSWORD`
- `SESSION_SECRET`
- `API_KEY_ENCRYPTION_KEY`

### 4. Database Setup and Migrations

```bash
# Create database ConfigMaps (migrations, seed data)
./k8s/create-db-configmaps.sh <NAMESPACE>

# Run database setup job (includes migrations)
kubectl apply -f k8s/eks/db-setup-job.yaml -n <NAMESPACE>

# Wait for completion
kubectl wait --for=condition=complete --timeout=300s job/db-setup -n <NAMESPACE>
```

The `db-setup-job.yaml` automatically:
- Waits for PostgreSQL to be ready
- Enables required extensions (uuid-ossp, vector)
- Runs base schema initialization
- Applies all migrations in order
- Seeds sample data (if database is empty)
- Tracks migrations in `schema_migrations` table

### 5. Deploy Application

#### Using Deployment Script (Recommended)

```bash
./scripts/deploy-eks-production.sh <NAMESPACE> <BACKEND_TAG> <FRONTEND_TAG>
```

Example:
```bash
./scripts/deploy-eks-production.sh 20890-ideaforge-ai-dev-58a50 fab20a2 e1dc1da
```

#### Manual Deployment

```bash
# Update image tags in deployment files
sed -i "s|image:.*ideaforge-ai-backend.*|image: ideaforge-ai-backend:<TAG>|g" k8s/eks/backend.yaml
sed -i "s|image:.*ideaforge-ai-frontend.*|image: ideaforge-ai-frontend:<TAG>|g" k8s/eks/frontend.yaml

# Apply deployments
kubectl apply -f k8s/eks/backend.yaml -n <NAMESPACE>
kubectl apply -f k8s/eks/frontend.yaml -n <NAMESPACE>

# Wait for rollout
kubectl rollout status deployment/backend -n <NAMESPACE>
kubectl rollout status deployment/frontend -n <NAMESPACE>
```

### 6. Verification

#### Quick Verification Script

```bash
./scripts/verify-deployment.sh <NAMESPACE> [CONTEXT]
```

#### Manual Verification

1. **Check Pods**
   ```bash
   kubectl get pods -n <NAMESPACE>
   ```

2. **Check Secrets**
   ```bash
   kubectl get secret ideaforge-ai-secrets -n <NAMESPACE> -o yaml
   ```

3. **Check Backend Logs for Agno Initialization**
   ```bash
   BACKEND_POD=$(kubectl get pods -n <NAMESPACE> -l app=backend -o jsonpath='{.items[0].metadata.name}')
   kubectl logs -n <NAMESPACE> $BACKEND_POD | grep -i "agno\|orchestrator\|provider"
   ```

   Look for:
   - `"agno_orchestrator_initialized"` - Agno is working
   - `"startup_provider_status"` - Shows which providers are configured
   - `"agno_framework_ready_at_startup"` - Success message

4. **Check Health Endpoint**
   ```bash
   kubectl port-forward -n <NAMESPACE> svc/backend 8000:8000
   curl http://localhost:8000/health
   ```

## Troubleshooting

### Agno Not Initializing

**Symptoms:**
- Backend logs show `"legacy_orchestrator_initialized"`
- No AI providers configured

**Solutions:**

1. **Verify API keys in secrets:**
   ```bash
   kubectl get secret ideaforge-ai-secrets -n <NAMESPACE> -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
   ```

2. **Check environment variables in pod:**
   ```bash
   kubectl exec -n <NAMESPACE> <BACKEND_POD> -- env | grep API_KEY
   ```

3. **Reload secrets and restart pods:**
   ```bash
   make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>
   kubectl rollout restart deployment/backend -n <NAMESPACE>
   ```

4. **Check backend logs:**
   ```bash
   kubectl logs -n <NAMESPACE> <BACKEND_POD> | grep -i "provider\|agno"
   ```

### Database Migration Issues

**Symptoms:**
- `db-setup` job fails
- Migrations not applied

**Solutions:**

1. **Check job logs:**
   ```bash
   kubectl logs -n <NAMESPACE> job/db-setup
   ```

2. **Verify ConfigMaps exist:**
   ```bash
   kubectl get configmap db-migrations -n <NAMESPACE>
   kubectl get configmap db-seed -n <NAMESPACE>
   ```

3. **Recreate ConfigMaps:**
   ```bash
   ./k8s/create-db-configmaps.sh <NAMESPACE>
   ```

4. **Manual migration (if needed):**
   ```bash
   kubectl apply -f k8s/eks/db-migration-job.yaml -n <NAMESPACE>
   ```

### Pods Not Starting

**Symptoms:**
- Pods in `CrashLoopBackOff` or `Pending`

**Solutions:**

1. **Check pod events:**
   ```bash
   kubectl describe pod <POD_NAME> -n <NAMESPACE>
   ```

2. **Check pod logs:**
   ```bash
   kubectl logs -n <NAMESPACE> <POD_NAME>
   ```

3. **Verify image exists:**
   ```bash
   kubectl get pod <POD_NAME> -n <NAMESPACE> -o jsonpath='{.spec.containers[0].image}'
   ```

## Clean Install vs Upgrade

### Clean Install

For a fresh installation:

1. Create namespace
2. Deploy PostgreSQL and Redis
3. Run `db-setup-job` (creates schema and runs migrations)
4. Deploy backend and frontend
5. Load secrets

### Upgrade

For upgrading existing installation:

1. **Backup database** (critical!)
2. Run `db-migration-job` (applies new migrations with backup)
3. Update image tags in deployments
4. Rollout new deployments
5. Verify Agno initialization

## Production Best Practices

1. **Always backup before migrations**
2. **Use External Secrets Operator** for production (not plain YAML)
3. **Monitor pod logs** after deployment
4. **Verify Agno initialization** in logs
5. **Test health endpoints** after deployment
6. **Use rolling updates** (default) for zero-downtime
7. **Set resource limits** in production deployments
8. **Enable HPA** for auto-scaling

## Post-Deployment Checklist

- [ ] All pods running and healthy
- [ ] Database migrations completed
- [ ] API keys configured in secrets
- [ ] Agno framework initialized (check logs)
- [ ] Health endpoints responding
- [ ] Frontend accessible via ingress
- [ ] Backend API responding
- [ ] Database backup created (before upgrade)

## Rollback Procedure

If deployment fails:

1. **Rollback deployments:**
   ```bash
   kubectl rollout undo deployment/backend -n <NAMESPACE>
   kubectl rollout undo deployment/frontend -n <NAMESPACE>
   ```

2. **Restore database (if needed):**
   ```bash
   kubectl exec -n <NAMESPACE> <POSTGRES_POD> -- psql -U agentic_pm -d agentic_pm_db < backups/eks_db_backup_<TIMESTAMP>.sql
   ```

3. **Verify rollback:**
   ```bash
   ./scripts/verify-deployment.sh <NAMESPACE>
   ```

