# EKS STG Environment Deployment Guide

This guide explains how to deploy IdeaForge AI to the EKS STG (Staging) environment, which is a complete clone of the DEV environment.

## Overview

The STG environment (`20890-ideaforge-ai-stg-60df9`) is configured to:
- Serve up to 150 concurrent users (vs 100 in DEV)
- Use separate ingress URLs for staging
- Have its own database instance (restored from latest DEV dump)
- Use separate McKinsey SSO OAuth client credentials
- Maintain complete isolation from DEV environment

## Prerequisites

1. **Kubeconfig**: STG environment kubeconfig stored at `/tmp/kubeconfig.wUHiei`
2. **Database Dump**: Latest database dump from DEV environment (created in last 15-30 mins)
3. **GitHub Token**: For pulling images from GHCR
4. **Environment File**: `env.eks.stg` with STG-specific configuration

## Configuration Files

### Environment Variables (`env.eks.stg`)

The STG environment uses `env.eks.stg` for configuration. Key differences from DEV:

- **Namespace**: `20890-ideaforge-ai-stg-60df9`
- **Frontend URL**: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
- **Backend URL**: `https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
- **McKinsey SSO Redirect URI**: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/api/auth/mckinsey/callback`

### Kubernetes Manifests

STG-specific manifests are located in:
- `k8s/eks/ingress-alb-stg.yaml` - Ingress configuration for STG
- `k8s/eks/hpa-backend-stg.yaml` - HPA for backend (8-30 replicas for 150 users)
- `k8s/eks/hpa-frontend-stg.yaml` - HPA for frontend (5-15 replicas for 150 users)
- `k8s/eks/postgres-ha-etcd-stg.yaml` - etcd cluster for STG
- `k8s/eks/postgres-ha-statefulset-stg.yaml` - PostgreSQL HA for STG
- `k8s/eks/db-restore-stg-job.yaml` - Database restore job from DEV dump
- `k8s/overlays/eks-20890-ideaforge-ai-stg-60df9/` - Kustomize overlay for STG

## Deployment Steps

### 1. Prepare Environment

```bash
# Ensure you have the kubeconfig
export KUBECONFIG=/tmp/kubeconfig.wUHiei

# Verify cluster access
kubectl cluster-info

# Set image tags (optional, defaults to latest)
export BACKEND_IMAGE_TAG=latest
export FRONTEND_IMAGE_TAG=latest
```

### 2. Update Environment File

Edit `env.eks.stg` and ensure:
- All API keys are set
- Database password is configured
- McKinsey SSO credentials are set (separate from DEV)
- All URLs point to STG environment

### 3. Run Deployment Script

```bash
# Make script executable (if not already)
chmod +x scripts/deploy-eks-stg.sh

# Run deployment
./scripts/deploy-eks-stg.sh
```

The script will:
1. Verify cluster access
2. Create namespace
3. Setup GHCR secret
4. Load secrets from `env.eks.stg`
5. Create database dump ConfigMap from latest DEV dump
6. Create database ConfigMaps (migrations, seed, init scripts)
7. Update namespace in all manifests
8. Deploy PostgreSQL HA (etcd + postgres)
9. Restore database from DEV dump
10. Deploy backend and frontend
11. Deploy HPA for 150 users
12. Deploy ingress

### 4. Manual Deployment (Alternative)

If you prefer manual deployment:

```bash
# Set namespace
export STG_NAMESPACE=20890-ideaforge-ai-stg-60df9
export KUBECONFIG=/tmp/kubeconfig.wUHiei

# Create namespace
kubectl create namespace ${STG_NAMESPACE}

# Setup GHCR secret
make eks-setup-ghcr-secret EKS_NAMESPACE=${STG_NAMESPACE}

# Load secrets
make eks-load-secrets EKS_NAMESPACE=${STG_NAMESPACE}

# Create database dump ConfigMap
LATEST_DUMP=$(find . -name "*.sql" -type f -mmin -30 | head -1)
kubectl create configmap db-dump-stg \
  --from-file=db_backup.sql="${LATEST_DUMP}" \
  --namespace=${STG_NAMESPACE}

# Create database ConfigMaps
EKS_NAMESPACE=${STG_NAMESPACE} bash k8s/create-db-configmaps.sh

# Deploy etcd
kubectl apply -f k8s/eks/postgres-ha-etcd-stg.yaml

# Deploy PostgreSQL HA
kubectl apply -f k8s/eks/postgres-ha-statefulset-stg.yaml

# Wait for PostgreSQL
kubectl wait --for=condition=ready pod -l app=postgres-ha -n ${STG_NAMESPACE} --timeout=600s

# Restore database
kubectl apply -f k8s/eks/db-restore-stg-job.yaml
kubectl wait --for=condition=complete job/db-restore-stg -n ${STG_NAMESPACE} --timeout=1800s

# Deploy backend and frontend
kubectl apply -f k8s/eks/backend.yaml
kubectl apply -f k8s/eks/frontend.yaml

# Deploy HPA
kubectl apply -f k8s/eks/hpa-backend-stg.yaml
kubectl apply -f k8s/eks/hpa-frontend-stg.yaml

# Deploy ingress
kubectl apply -f k8s/eks/ingress-alb-stg.yaml
```

## Post-Deployment

### 1. Update McKinsey SSO Configuration

**IMPORTANT**: Register the STG redirect URI with McKinsey Identity Platform:

```
https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/api/auth/mckinsey/callback
```

Contact the McKinsey Identity Platform team to:
1. Create a separate OAuth client for STG environment
2. Register the STG redirect URI
3. Provide STG-specific Client ID and Client Secret

Update `env.eks.stg` with the STG credentials and reload secrets:

```bash
make eks-load-secrets EKS_NAMESPACE=20890-ideaforge-ai-stg-60df9
```

### 2. Verify Deployment

```bash
# Check all resources
kubectl get all -n 20890-ideaforge-ai-stg-60df9

# Check ingress
kubectl get ingress -n 20890-ideaforge-ai-stg-60df9

# Check HPA
kubectl get hpa -n 20890-ideaforge-ai-stg-60df9

# Check database restore job
kubectl logs -n 20890-ideaforge-ai-stg-60df9 job/db-restore-stg
```

### 3. Test Application

- Frontend: `https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
- Backend API: `https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud`
- Health Check: `https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/health`

## Scaling Configuration

The STG environment is configured for **150 concurrent users**:

- **Backend HPA**: 8-30 replicas (min 8, max 30)
- **Frontend HPA**: 5-15 replicas (min 5, max 15)
- **PostgreSQL HA**: 3 replicas (1 primary + 2 replicas)
- **Redis**: 1 replica (can be scaled if needed)

## Database Management

### Restore from DEV Dump

To restore the database from a new DEV dump:

```bash
# Find latest dump
LATEST_DUMP=$(find . -name "*.sql" -type f -mmin -30 | head -1)

# Create/update ConfigMap
kubectl delete configmap db-dump-stg -n 20890-ideaforge-ai-stg-60df9 --ignore-not-found=true
kubectl create configmap db-dump-stg \
  --from-file=db_backup.sql="${LATEST_DUMP}" \
  --namespace=20890-ideaforge-ai-stg-60df9

# Run restore job
kubectl delete job db-restore-stg -n 20890-ideaforge-ai-stg-60df9 --ignore-not-found=true
kubectl apply -f k8s/eks/db-restore-stg-job.yaml
kubectl wait --for=condition=complete job/db-restore-stg -n 20890-ideaforge-ai-stg-60df9 --timeout=1800s
```

## Troubleshooting

### Database Restore Fails

```bash
# Check restore job logs
kubectl logs -n 20890-ideaforge-ai-stg-60df9 job/db-restore-stg

# Check PostgreSQL pods
kubectl get pods -n 20890-ideaforge-ai-stg-60df9 -l app=postgres-ha

# Check etcd cluster
kubectl get pods -n 20890-ideaforge-ai-stg-60df9 -l app=etcd
```

### Ingress Not Accessible

```bash
# Check ingress status
kubectl describe ingress -n 20890-ideaforge-ai-stg-60df9

# Check ALB controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

### McKinsey SSO Not Working

1. Verify redirect URI is registered with McKinsey Identity Platform
2. Check `MCKINSEY_REDIRECT_URI` in secrets matches registered URI exactly
3. Verify STG OAuth client credentials are correct
4. Check backend logs for SSO errors

## Differences from DEV

| Aspect | DEV | STG |
|--------|-----|-----|
| Namespace | `20890-ideaforge-ai-dev-58a50` | `20890-ideaforge-ai-stg-60df9` |
| Frontend URL | `ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud` | `ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud` |
| Backend URL | `api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud` | `api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud` |
| Min Backend Replicas | 5 | 8 |
| Max Backend Replicas | 20 | 30 |
| Min Frontend Replicas | 3 | 5 |
| Max Frontend Replicas | 10 | 15 |
| Target Users | 100 | 150 |
| Database | Independent | Restored from DEV dump |
| McKinsey SSO | Separate OAuth client | Separate OAuth client |

## Maintenance

### Update Application

```bash
# Set new image tags
export BACKEND_IMAGE_TAG=new-tag
export FRONTEND_IMAGE_TAG=new-tag

# Update deployments
kubectl set image deployment/backend backend=ghcr.io/soumantrivedi/ideaforge-ai/backend:${BACKEND_IMAGE_TAG} -n 20890-ideaforge-ai-stg-60df9
kubectl set image deployment/frontend frontend=ghcr.io/soumantrivedi/ideaforge-ai/frontend:${FRONTEND_IMAGE_TAG} -n 20890-ideaforge-ai-stg-60df9
```

### Backup Database

```bash
# Create backup job (similar to DEV)
# TODO: Create backup job for STG
```

## Support

For issues or questions:
1. Check logs: `kubectl logs -n 20890-ideaforge-ai-stg-60df9 -l app=backend`
2. Check status: `kubectl get all -n 20890-ideaforge-ai-stg-60df9`
3. Review this documentation
4. Contact DevOps team

