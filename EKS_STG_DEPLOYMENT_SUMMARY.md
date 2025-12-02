# EKS STG Environment Deployment - Summary

## Overview

A complete STG (Staging) environment has been configured for IdeaForge AI in EKS, cloned from the DEV environment with all necessary configurations for serving 150 concurrent users.

## What Was Created

### 1. Kustomize Overlay
- **Location**: `k8s/overlays/eks-20890-ideaforge-ai-stg-60df9/`
- **Files**:
  - `namespace-patch.yaml` - STG namespace definition
  - `imagepullsecret-patch.yaml` - GHCR secret configuration
  - `kustomization.yaml` - Kustomize configuration

### 2. Environment Configuration
- **File**: `env.eks.stg`
- **Contains**: STG-specific environment variables including:
  - Namespace: `20890-ideaforge-ai-stg-60df9`
  - Frontend URL: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
  - Backend URL: `https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
  - McKinsey SSO redirect URI for STG

### 3. Kubernetes Manifests (STG-specific)
- **Ingress**: `k8s/eks/ingress-alb-stg.yaml`
  - Configured for STG external names
  - Separate ALB with STG tags
  
- **HPA (Backend)**: `k8s/eks/hpa-backend-stg.yaml`
  - Min replicas: 8 (for 150 users)
  - Max replicas: 30
  
- **HPA (Frontend)**: `k8s/eks/hpa-frontend-stg.yaml`
  - Min replicas: 5 (for 150 users)
  - Max replicas: 15

- **PostgreSQL HA**: 
  - `k8s/eks/postgres-ha-etcd-stg.yaml` - etcd cluster for STG
  - `k8s/eks/postgres-ha-statefulset-stg.yaml` - PostgreSQL HA StatefulSet for STG

- **Database Restore**: `k8s/eks/db-restore-stg-job.yaml`
  - Restores database from latest DEV dump
  - Creates ConfigMap from SQL dump file

### 4. Deployment Script
- **File**: `scripts/deploy-eks-stg.sh`
- **Purpose**: Automated deployment script that:
  1. Verifies cluster access
  2. Creates namespace
  3. Sets up GHCR secret
  4. Loads secrets from `env.eks.stg`
  5. Creates database dump ConfigMap
  6. Deploys all components
  7. Restores database from DEV dump

### 5. Documentation
- **File**: `docs/deployment/EKS_STG_DEPLOYMENT.md`
- **Contains**: Complete deployment guide with troubleshooting

## Key Configuration Differences from DEV

| Component | DEV | STG |
|-----------|-----|-----|
| Namespace | `20890-ideaforge-ai-dev-58a50` | `20890-ideaforge-ai-stg-60df9` |
| Frontend URL | `ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud` | `ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud` |
| Backend URL | `api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud` | `api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud` |
| Backend Min Replicas | 5 | 8 |
| Backend Max Replicas | 20 | 30 |
| Frontend Min Replicas | 3 | 5 |
| Frontend Max Replicas | 10 | 15 |
| Target Users | 100 | 150 |
| Database Source | Independent | Restored from DEV dump |
| McKinsey SSO | Separate client | Separate client (needs registration) |

## Deployment Steps

### Quick Deploy

```bash
# 1. Ensure kubeconfig is available
export KUBECONFIG=/tmp/kubeconfig.wUHiei

# 2. Update env.eks.stg with your credentials
# Edit env.eks.stg and fill in:
#   - POSTGRES_PASSWORD
#   - All API keys
#   - McKinsey SSO credentials (STG-specific)

# 3. Run deployment script
./scripts/deploy-eks-stg.sh
```

### Manual Deploy

See `docs/deployment/EKS_STG_DEPLOYMENT.md` for detailed manual deployment steps.

## Post-Deployment Checklist

- [ ] Verify all pods are running: `kubectl get pods -n 20890-ideaforge-ai-stg-60df9`
- [ ] Check ingress is accessible: `kubectl get ingress -n 20890-ideaforge-ai-stg-60df9`
- [ ] Verify database restore completed: `kubectl logs -n 20890-ideaforge-ai-stg-60df9 job/db-restore-stg`
- [ ] Test frontend URL: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
- [ ] Test backend API: `https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/health`
- [ ] **Register McKinsey SSO redirect URI** with McKinsey Identity Platform:
  - URI: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/api/auth/mckinsey/callback`
  - Request separate OAuth client for STG environment
- [ ] Update `env.eks.stg` with STG McKinsey SSO credentials
- [ ] Reload secrets: `make eks-load-secrets EKS_NAMESPACE=20890-ideaforge-ai-stg-60df9`
- [ ] Test McKinsey SSO login flow

## Database Restore

The deployment script automatically:
1. Finds the latest database dump (created in last 15-30 mins)
2. Creates a ConfigMap from the dump file
3. Runs a restore job to populate the STG database

If you need to restore from a different dump:

```bash
# Create ConfigMap from specific dump
kubectl delete configmap db-dump-stg -n 20890-ideaforge-ai-stg-60df9 --ignore-not-found=true
kubectl create configmap db-dump-stg \
  --from-file=db_backup.sql=/path/to/dump.sql \
  --namespace=20890-ideaforge-ai-stg-60df9

# Run restore job
kubectl delete job db-restore-stg -n 20890-ideaforge-ai-stg-60df9 --ignore-not-found=true
kubectl apply -f k8s/eks/db-restore-stg-job.yaml
kubectl wait --for=condition=complete job/db-restore-stg -n 20890-ideaforge-ai-stg-60df9 --timeout=1800s
```

## Scaling for 150 Users

The STG environment is configured to handle 150 concurrent users with:

- **Backend**: 8-30 replicas (HPA configured)
- **Frontend**: 5-15 replicas (HPA configured)
- **PostgreSQL HA**: 3 replicas (1 primary + 2 replicas)
- **Redis**: 1 replica (can be scaled if needed)

HPA will automatically scale based on CPU and memory utilization.

## Important Notes

1. **McKinsey SSO**: STG requires separate OAuth client credentials. Contact McKinsey Identity Platform team to register the STG redirect URI.

2. **Database**: STG database is restored from DEV dump. Any changes in STG will not affect DEV.

3. **Isolation**: STG is completely isolated from DEV - separate namespace, ingress, database, and secrets.

4. **Kubeconfig**: Uses `/tmp/kubeconfig.wUHiei` for STG cluster access.

5. **Image Tags**: Defaults to `latest`. Set `BACKEND_IMAGE_TAG` and `FRONTEND_IMAGE_TAG` environment variables to use specific versions.

## Troubleshooting

See `docs/deployment/EKS_STG_DEPLOYMENT.md` for detailed troubleshooting guide.

Common issues:
- Database restore fails → Check dump file and PostgreSQL pods
- Ingress not accessible → Check ALB controller and ingress status
- McKinsey SSO not working → Verify redirect URI registration and credentials

## Files Created/Modified

### New Files
- `k8s/overlays/eks-20890-ideaforge-ai-stg-60df9/namespace-patch.yaml`
- `k8s/overlays/eks-20890-ideaforge-ai-stg-60df9/imagepullsecret-patch.yaml`
- `k8s/overlays/eks-20890-ideaforge-ai-stg-60df9/kustomization.yaml`
- `env.eks.stg`
- `k8s/eks/ingress-alb-stg.yaml`
- `k8s/eks/hpa-backend-stg.yaml`
- `k8s/eks/hpa-frontend-stg.yaml`
- `k8s/eks/postgres-ha-etcd-stg.yaml`
- `k8s/eks/postgres-ha-statefulset-stg.yaml`
- `k8s/eks/db-restore-stg-job.yaml`
- `scripts/deploy-eks-stg.sh`
- `docs/deployment/EKS_STG_DEPLOYMENT.md`
- `EKS_STG_DEPLOYMENT_SUMMARY.md` (this file)

### Modified Files
- None (all changes are in new STG-specific files)

## Next Steps

1. Review and update `env.eks.stg` with actual credentials
2. Run deployment script: `./scripts/deploy-eks-stg.sh`
3. Register McKinsey SSO redirect URI
4. Verify deployment and test application
5. Monitor HPA scaling behavior

## Support

For questions or issues:
- Review `docs/deployment/EKS_STG_DEPLOYMENT.md`
- Check pod logs: `kubectl logs -n 20890-ideaforge-ai-stg-60df9 -l app=backend`
- Check deployment status: `kubectl get all -n 20890-ideaforge-ai-stg-60df9`

