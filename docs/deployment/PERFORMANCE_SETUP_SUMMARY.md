# Performance Setup Summary for 100 Concurrent Users

## Overview

This setup pre-warms the EKS production environment and provides tools to test 100 concurrent users making multi-agent queries.

## Quick Setup (3 Steps)

### Step 1: Setup HPA (Horizontal Pod Autoscaler)

```bash
export KUBECONFIG=/tmp/kubeconfig.tlnAhy
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

make eks-setup-hpa EKS_NAMESPACE=$EKS_NAMESPACE
```

This configures:
- **Backend HPA**: 5-20 replicas (scales based on CPU >70% or Memory >80%)
- **Frontend HPA**: 3-10 replicas (scales based on CPU >70% or Memory >80%)

### Step 2: Pre-warm Deployments

```bash
make eks-prewarm EKS_NAMESPACE=$EKS_NAMESPACE
```

This scales to minimum replicas:
- **Backend**: 5 replicas (1.5Gi-3Gi memory, 1-3 CPU cores each)
- **Frontend**: 3 replicas (256Mi-512Mi memory, 100m-500m CPU each)

### Step 3: Run Performance Test

```bash
# Get auth token from browser DevTools > Application > Cookies
export BASE_URL="https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud"
export AUTH_TOKEN="your-session-token"
export PRODUCT_ID="your-product-uuid"

make eks-performance-test \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BASE_URL=$BASE_URL \
  AUTH_TOKEN=$AUTH_TOKEN \
  PRODUCT_ID=$PRODUCT_ID
```

## Resource Configuration

### Backend
- **Min Replicas**: 5 (for 100 users baseline)
- **Max Replicas**: 20 (for burst capacity)
- **CPU Request**: 1000m (1 core)
- **CPU Limit**: 3000m (3 cores)
- **Memory Request**: 1.5Gi
- **Memory Limit**: 3Gi

### Frontend
- **Min Replicas**: 3 (for 100 users baseline)
- **Max Replicas**: 10 (for burst capacity)
- **CPU Request**: 100m (0.1 core)
- **CPU Limit**: 500m (0.5 core)
- **Memory Request**: 256Mi
- **Memory Limit**: 512Mi

## NFR Targets

The performance test validates these Non-Functional Requirements:

1. **Response Time (P95)**: < 30 seconds ✅
2. **Error Rate**: < 5% ✅
3. **Throughput**: > 2 requests/second ✅
4. **Quality Score**: > 60/100 ✅
5. **First Chunk Time (TTFB)**: < 5 seconds ✅

## Monitoring During Tests

### Watch Pod Scaling
```bash
watch -n 2 'kubectl get pods -n $EKS_NAMESPACE -l "app in (backend,frontend)"'
```

### Watch HPA
```bash
watch -n 2 'kubectl get hpa -n $EKS_NAMESPACE'
```

### Monitor Resource Usage
```bash
watch -n 2 'kubectl top pods -n $EKS_NAMESPACE -l "app in (backend,frontend)"'
```

## Expected Behavior

### During Test
- Backend pods should scale from 5 → 10-15 during peak load
- Frontend pods should scale from 3 → 5-7 during peak load
- CPU usage should trigger scaling at ~70% average
- Memory usage should trigger scaling at ~80% average

### Test Results
- **Total Requests**: ~200 (100 users × 2 queries each)
- **Success Rate**: > 95%
- **Average Response Time**: 15-25 seconds
- **P95 Response Time**: < 30 seconds
- **Throughput**: 3-5 requests/second

## Files Created

1. `k8s/eks/hpa-backend.yaml` - Backend HPA configuration
2. `k8s/eks/hpa-frontend.yaml` - Frontend HPA configuration
3. `scripts/performance-test.py` - Performance testing script
4. `scripts/performance-test-requirements.txt` - Python dependencies
5. `docs/deployment/PERFORMANCE_TESTING.md` - Detailed guide
6. `scripts/QUICK_PERFORMANCE_TEST.md` - Quick reference

## Makefile Targets

- `make eks-setup-hpa` - Setup HPA for auto-scaling
- `make eks-prewarm` - Pre-warm to minimum replicas
- `make eks-performance-test` - Run performance test

## Next Steps

1. Install test dependencies: `pip install -r scripts/performance-test-requirements.txt`
2. Run setup: `make eks-setup-hpa EKS_NAMESPACE=...`
3. Pre-warm: `make eks-prewarm EKS_NAMESPACE=...`
4. Run test: `make eks-performance-test ...`

