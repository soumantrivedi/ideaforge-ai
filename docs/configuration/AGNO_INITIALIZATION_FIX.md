# Agno Initialization Fix - Production Deployment

## Problem

In production deployments (EKS), Agno agents were not initializing because:
1. API keys from Kubernetes secrets were not being properly loaded into the provider registry
2. The provider registry was initialized at module load time, before environment variables from Kubernetes secrets were available
3. No mechanism to refresh provider clients after secrets were loaded

## Solution

### 1. Enhanced Startup Initialization (`backend/main.py`)

The `lifespan` function now:
- **Rebuilds provider clients** before initializing orchestrator to ensure latest values from environment variables
- **Logs detailed provider status** for troubleshooting
- **Provides clear warnings** when providers are not configured

Key changes:
```python
# Force re-check of provider registry to ensure it has latest values from environment
provider_registry._rebuild_clients()

# Reinitialize orchestrator with updated provider registry
orchestrator, agno_enabled = _initialize_orchestrator()
```

### 2. Provider Registry Improvements (`backend/services/provider_registry.py`)

- Added error logging in `_rebuild_clients()` for troubleshooting
- Made `_rebuild_clients()` public so it can be called to refresh clients after keys are updated

### 3. Deployment Scripts

Created comprehensive deployment scripts:

#### `scripts/deploy-eks-production.sh`
- Handles complete EKS deployment process
- Database backup before migrations
- Secrets and ConfigMaps loading
- Database setup and migrations
- Application deployment
- Verification

#### `scripts/verify-deployment.sh`
- Verifies deployment health
- Checks API keys in secrets
- Verifies Agno initialization from logs
- Provides actionable feedback

## Deployment Process

### For Clean Install

1. **Load Secrets:**
   ```bash
   # For Kind (local development)
   make kind-load-secrets
   
   # For EKS (production)
   make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>
   ```

2. **Create Database ConfigMaps:**
   ```bash
   ./k8s/create-db-configmaps.sh <NAMESPACE>
   ```

3. **Run Database Setup:**
   ```bash
   kubectl apply -f k8s/eks/db-setup-job.yaml -n <NAMESPACE>
   kubectl wait --for=condition=complete job/db-setup -n <NAMESPACE>
   ```

4. **Deploy Application:**
   ```bash
   ./scripts/deploy-eks-production.sh <NAMESPACE> <BACKEND_TAG> <FRONTEND_TAG>
   ```

5. **Verify:**
   ```bash
   ./scripts/verify-deployment.sh <NAMESPACE>
   ```

### For Upgrade

1. **Backup Database:**
   ```bash
   # Automatic in deploy script, or manual:
   kubectl exec -n <NAMESPACE> <POSTGRES_POD> -- pg_dump -U agentic_pm -d agentic_pm_db > backup.sql
   ```

2. **Run Migrations:**
   ```bash
   kubectl apply -f k8s/eks/db-migration-job.yaml -n <NAMESPACE>
   ```

3. **Update Secrets (if needed):**
   ```bash
   make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>
   ```

4. **Deploy Application:**
   ```bash
   ./scripts/deploy-eks-production.sh <NAMESPACE> <BACKEND_TAG> <FRONTEND_TAG>
   ```

5. **Verify:**
   ```bash
   ./scripts/verify-deployment.sh <NAMESPACE>
   ```

## Verification

### Check API Keys in Secrets

```bash
kubectl get secret ideaforge-ai-secrets -n <NAMESPACE> -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
```

### Check Backend Logs for Agno

```bash
BACKEND_POD=$(kubectl get pods -n <NAMESPACE> -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n <NAMESPACE> $BACKEND_POD | grep -i "agno\|orchestrator\|provider"
```

**Look for:**
- ✅ `"agno_orchestrator_initialized"` - Agno is working
- ✅ `"agno_framework_ready_at_startup"` - Success
- ⚠️ `"agno_framework_waiting_for_providers"` - No API keys configured
- ⚠️ `"legacy_orchestrator_initialized"` - Agno not enabled

### Expected Log Output

When properly configured:
```json
{
  "event": "startup_provider_status",
  "providers": ["openai"],
  "has_openai": true,
  "has_claude": false,
  "has_gemini": false
}
{
  "event": "startup_orchestrator_status",
  "orchestrator_type": "AgnoAgenticOrchestrator",
  "agno_enabled": true,
  "has_providers": true
}
{
  "event": "agno_framework_ready_at_startup",
  "providers": ["openai"],
  "message": "Agno framework initialized successfully from environment variables (Kubernetes secrets)"
}
```

## Troubleshooting

### Agno Not Initializing

1. **Check secrets are loaded:**
   ```bash
   kubectl get secret ideaforge-ai-secrets -n <NAMESPACE> -o yaml
   ```

2. **Check environment variables in pod:**
   ```bash
   kubectl exec -n <NAMESPACE> <BACKEND_POD> -- env | grep API_KEY
   ```

3. **Reload secrets and restart:**
   ```bash
   make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>
   kubectl rollout restart deployment/backend -n <NAMESPACE>
   ```

4. **Check logs for errors:**
   ```bash
   kubectl logs -n <NAMESPACE> <BACKEND_POD> | grep -i "error\|warning\|agno"
   ```

### Empty API Keys

If secrets exist but keys are empty:
1. Update `.env` file with actual API keys
2. Run: `make eks-load-secrets EKS_NAMESPACE=<NAMESPACE>`
3. Restart backend: `kubectl rollout restart deployment/backend -n <NAMESPACE>`

## Key Files Modified

1. `backend/main.py` - Enhanced startup initialization with provider registry refresh
2. `backend/services/provider_registry.py` - Improved error handling and public rebuild method
3. `scripts/deploy-eks-production.sh` - Comprehensive deployment script
4. `scripts/verify-deployment.sh` - Deployment verification script
5. `docs/DEPLOYMENT_PRODUCTION.md` - Complete production deployment guide

## Next Steps for EKS Production

1. **Configure API keys in `.env` file:**
   ```bash
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   GOOGLE_API_KEY=...
   ```

2. **Run deployment:**
   ```bash
   ./scripts/deploy-eks-production.sh <NAMESPACE> <BACKEND_TAG> <FRONTEND_TAG>
   ```

3. **Verify:**
   ```bash
   ./scripts/verify-deployment.sh <NAMESPACE>
   ```

4. **Check logs:**
   ```bash
   kubectl logs -n <NAMESPACE> -l app=backend | grep -i "agno\|provider"
   ```

The system will now properly initialize Agno agents when API keys are configured in Kubernetes secrets.

