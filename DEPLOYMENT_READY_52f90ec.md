# Deployment Ready - Image Tag 52f90ec

**Date**: $(date)
**Namespace**: `20890-ideaforge-ai-dev-58a50`
**Kubeconfig**: `/tmp/kubeconfig.eacSiD`

## ✅ Configuration Applied

### ConfigMap Updated
- ✅ `JOB_POLL_INTERVAL_MS`: `5000` (5 seconds)
- ✅ `JOB_MAX_POLL_ATTEMPTS`: `60` (5 minutes total)
- ✅ `JOB_TIMEOUT_MS`: `300000` (5 minutes)

### Deployments Rolled Out
- ✅ Frontend deployment restarted to pick up new ConfigMap values
- ✅ Frontend pods running with new configuration

## 📦 Ready for Image Deployment

**Current Image Tags**:
- Backend: `ghcr.io/soumantrivedi/ideaforge-ai/backend:1a7d883`
- Frontend: `ghcr.io/soumantrivedi/ideaforge-ai/frontend:1a7d883`

**New Image Tags** (after GitHub Actions build completes):
- Backend: `ghcr.io/soumantrivedi/ideaforge-ai/backend:52f90ec`
- Frontend: `ghcr.io/soumantrivedi/ideaforge-ai/frontend:52f90ec`

## 🚀 Deployment Commands (Run after images are built)

```bash
export KUBECONFIG=/tmp/kubeconfig.eacSiD
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
export NEW_TAG=52f90ec

# Clean old replicasets
kubectl get replicasets -n $EKS_NAMESPACE -o json | \
  jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' | \
  while read rs; do kubectl delete replicaset "$rs" -n $EKS_NAMESPACE --ignore-not-found=true; done

# Update images
kubectl set image deployment/backend \
  backend=ghcr.io/soumantrivedi/ideaforge-ai/backend:$NEW_TAG \
  -n $EKS_NAMESPACE

kubectl set image deployment/frontend \
  frontend=ghcr.io/soumantrivedi/ideaforge-ai/frontend:$NEW_TAG \
  -n $EKS_NAMESPACE

# Wait for rollout
kubectl rollout status deployment/backend -n $EKS_NAMESPACE --timeout=300s
kubectl rollout status deployment/frontend -n $EKS_NAMESPACE --timeout=300s

# Verify
kubectl get pods -n $EKS_NAMESPACE -l 'app in (backend,frontend)'
```

## 📋 Changes in This Deployment

### Backend (52f90ec)
- ✅ Fixed datetime serialization using `field_serializer`
- ✅ Optimized prompt structure (SYSTEM CONTEXT / USER REQUEST)
- ✅ Reduced context size for better performance
- ✅ Better agent coordination with separated prompts

### Frontend (52f90ec)
- ✅ Configurable polling interval (reads from ConfigMap)
- ✅ Updated default timeout to 5 minutes
- ✅ Cleaner query structure
- ✅ Better error handling

### Configuration
- ✅ Job timeout: 5 minutes (300000ms)
- ✅ Max polling attempts: 60
- ✅ Polling interval: 5 seconds (configurable)

## ⏳ Waiting for Images

GitHub Actions is building images with tag `52f90ec`. Once complete:
1. Verify images exist: `docker pull ghcr.io/soumantrivedi/ideaforge-ai/backend:52f90ec`
2. Run deployment commands above
3. Verify deployment

## 🔍 Verification After Deployment

```bash
# Check pods
kubectl get pods -n $EKS_NAMESPACE -l 'app in (backend,frontend)'

# Check image tags
kubectl get deployment backend -n $EKS_NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl get deployment frontend -n $EKS_NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}'

# Test async endpoint
curl -X POST https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api/multi-agent/submit \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request": {"user_id": "...", "query": "test"}}'
```

