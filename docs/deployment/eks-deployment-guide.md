# EKS Production Deployment Guide

## Overview

This guide walks through deploying the async job processing changes to EKS production cluster.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **kubectl configured** for EKS cluster
3. **Docker** running and logged into GHCR
4. **Git** with all changes committed
5. **EKS_NAMESPACE** environment variable set (e.g., `20890-ideaforge-ai-dev-58a50`)

## Deployment Steps

### Step 1: Commit and Push Changes

```bash
# Stage all changes
git add backend/ src/ docs/

# Commit with descriptive message
git commit -m "feat: Add async job processing for multi-agent requests to avoid Cloudflare timeouts"

# Push to both remotes
git push origin main
git push mck-internal main
```

### Step 2: Build and Push Docker Images

The GitHub Actions workflow will automatically build and push images when you push to main. However, you can also build manually:

```bash
# Get current git SHA for image tags
GIT_SHA=$(git rev-parse --short HEAD)
echo "Building images with tag: $GIT_SHA"

# Build backend image
docker build -f Dockerfile.backend \
  --build-arg GIT_SHA=$GIT_SHA \
  --build-arg VERSION=$GIT_SHA \
  -t ghcr.io/soumantrivedi/ideaforge-ai/backend:$GIT_SHA \
  -t ghcr.io/soumantrivedi/ideaforge-ai/backend:latest \
  .

# Build frontend image
docker build -f Dockerfile.frontend \
  --build-arg GIT_SHA=$GIT_SHA \
  --build-arg VERSION=$GIT_SHA \
  -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:$GIT_SHA \
  -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:latest \
  .

# Login to GHCR (if not already)
echo $GITHUB_TOKEN | docker login ghcr.io -u soumantrivedi --password-stdin

# Push images
docker push ghcr.io/soumantrivedi/ideaforge-ai/backend:$GIT_SHA
docker push ghcr.io/soumantrivedi/ideaforge-ai/backend:latest
docker push ghcr.io/soumantrivedi/ideaforge-ai/frontend:$GIT_SHA
docker push ghcr.io/soumantrivedi/ideaforge-ai/frontend:latest
```

### Step 3: Update EKS Manifests

Update the image tags in EKS manifests:

```bash
# Get current git SHA
GIT_SHA=$(git rev-parse --short HEAD)

# Update backend.yaml
sed -i '' "s|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:$GIT_SHA|g" k8s/eks/backend.yaml

# Update frontend.yaml
sed -i '' "s|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$GIT_SHA|g" k8s/eks/frontend.yaml
```

### Step 4: Deploy to EKS

```bash
# Set EKS namespace
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50  # Update with your namespace

# Set image tags
export BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD)
export FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)

# Full deployment (includes GHCR secret setup, namespace prep, secrets, and deploy)
make eks-deploy-full \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$BACKEND_IMAGE_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_IMAGE_TAG
```

### Step 5: Verify Deployment

```bash
# Check pod status
kubectl get pods -n $EKS_NAMESPACE

# Check backend logs for new endpoints
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=50 | grep -i "job\|async"

# Test new async endpoint
curl -X POST https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api/multi-agent/submit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request": {"user_id": "...", "query": "test"}}'

# Check job status
curl -X GET https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api/multi-agent/jobs/{job_id}/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Quick Deployment Command

For a single command deployment (after images are built and pushed):

```bash
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
export BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD)
export FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)

make eks-deploy-full \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$BACKEND_IMAGE_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_IMAGE_TAG
```

## Rollback Procedure

If deployment fails, rollback to previous version:

```bash
# Get previous image tag (from git history or previous deployment)
PREVIOUS_TAG=0e0a776  # Update with actual previous tag

# Update manifests
sed -i '' "s|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:$PREVIOUS_TAG|g" k8s/eks/backend.yaml
sed -i '' "s|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$PREVIOUS_TAG|g" k8s/eks/frontend.yaml

# Redeploy
make eks-deploy EKS_NAMESPACE=$EKS_NAMESPACE BACKEND_IMAGE_TAG=$PREVIOUS_TAG FRONTEND_IMAGE_TAG=$PREVIOUS_TAG
```

## Post-Deployment Checklist

- [ ] All pods are running (`kubectl get pods -n $EKS_NAMESPACE`)
- [ ] Backend logs show new async endpoints registered
- [ ] Frontend can submit async jobs
- [ ] Job status polling works
- [ ] Job results are returned correctly
- [ ] No Cloudflare 524 errors in production
- [ ] Redis is handling job storage correctly
- [ ] Monitor Redis memory usage

## Monitoring

Monitor these metrics after deployment:

1. **Job Success Rate**: Check backend logs for job completion
2. **Redis Memory**: `kubectl exec -n $EKS_NAMESPACE -it deployment/redis -- redis-cli INFO memory`
3. **Response Times**: Monitor async job processing times
4. **Error Rates**: Check for any new errors in backend logs

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod -n $EKS_NAMESPACE -l app=backend

# Check logs
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=100
```

### Image Pull Errors

```bash
# Verify GHCR secret exists
kubectl get secret ghcr-secret -n $EKS_NAMESPACE

# Recreate secret if needed
make eks-setup-ghcr-secret EKS_NAMESPACE=$EKS_NAMESPACE
```

### Redis Connection Issues

```bash
# Check Redis pod
kubectl get pods -n $EKS_NAMESPACE -l app=redis

# Test Redis connection from backend pod
kubectl exec -n $EKS_NAMESPACE -it deployment/backend -- python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

