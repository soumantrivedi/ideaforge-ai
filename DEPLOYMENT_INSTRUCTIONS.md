# EKS Production Deployment Instructions

## Prerequisites

1. **AWS CLI configured** with credentials
2. **kubectl** installed
3. **Access to EKS cluster** `ideaforge-ai` in region `us-east-1`
4. **Namespace exists**: `20890-ideaforge-ai-dev-58a50`

## Step 1: Configure AWS and kubectl

```bash
# Configure AWS CLI (if not already done)
aws configure

# Update kubectl context for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get namespace 20890-ideaforge-ai-dev-58a50
```

## Step 2: Clean Up Old Replicasets

```bash
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

# List old replicasets
kubectl get replicasets -n $EKS_NAMESPACE -o json | \
  jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' | \
  while read rs; do
    [ -n "$rs" ] && kubectl delete replicaset "$rs" -n $EKS_NAMESPACE --ignore-not-found=true
  done
```

## Step 3: Update Image Tags

```bash
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
export BACKEND_TAG=28a283d
export FRONTEND_TAG=28a283d

# Update backend deployment
kubectl set image deployment/backend \
  backend=ghcr.io/soumantrivedi/ideaforge-ai/backend:$BACKEND_TAG \
  -n $EKS_NAMESPACE

# Update frontend deployment
kubectl set image deployment/frontend \
  frontend=ghcr.io/soumantrivedi/ideaforge-ai/frontend:$FRONTEND_TAG \
  -n $EKS_NAMESPACE
```

## Step 4: Setup Secrets and ConfigMaps

```bash
# Setup GHCR secret (for pulling images)
make eks-setup-ghcr-secret EKS_NAMESPACE=$EKS_NAMESPACE

# Load secrets from .env
make eks-load-secrets EKS_NAMESPACE=$EKS_NAMESPACE

# Update ConfigMaps
EKS_NAMESPACE=$EKS_NAMESPACE bash k8s/create-db-configmaps.sh
```

## Step 5: Wait for Rollout

```bash
# Wait for backend rollout
kubectl rollout status deployment/backend -n $EKS_NAMESPACE --timeout=300s

# Wait for frontend rollout
kubectl rollout status deployment/frontend -n $EKS_NAMESPACE --timeout=300s
```

## Step 6: Verify Deployment

```bash
# Check pod status
kubectl get pods -n $EKS_NAMESPACE -l 'app in (backend,frontend)'

# Verify image tags
kubectl get deployment backend -n $EKS_NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl get deployment frontend -n $EKS_NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check backend logs for async endpoints
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=50 | grep -i "job\|async\|submit"
```

## Step 7: Verify Async Endpoints

```bash
# Run verification script
./scripts/verify-async-endpoints.sh $EKS_NAMESPACE
```

## Quick Deployment (All Steps)

```bash
# Run the complete deployment script
./scripts/deploy-eks-production.sh 20890-ideaforge-ai-dev-58a50
```

## Troubleshooting

### Images Not Found
If images are not available in GHCR, wait for GitHub Actions to complete:
- Check: https://github.com/soumantrivedi/ideaforge-ai/actions
- Wait for "Build and Publish Docker Images" workflow

### Pods Not Starting
```bash
# Check pod events
kubectl describe pod -n $EKS_NAMESPACE -l app=backend

# Check logs
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=100
```

### Redis Connection Issues
```bash
# Test Redis from backend pod
BACKEND_POD=$(kubectl get pods -n $EKS_NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $EKS_NAMESPACE $BACKEND_POD -- \
  python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print('OK' if r.ping() else 'FAIL')"
```

## Kind Cluster Deployment (Parallel)

The Kind cluster has been updated with the latest images. To verify:

```bash
# Switch to kind context
kubectl config use-context kind-ideaforge-ai

# Check status
kubectl get pods -n ideaforge-ai
make kind-status

# Test async endpoints locally
make kind-port-forward
# Then test: http://localhost:8000/api/multi-agent/submit
```

