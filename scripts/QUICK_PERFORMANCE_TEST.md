# Quick Performance Test Guide

## Quick Start (5 minutes)

### 1. Setup HPA and Pre-warm

```bash
export KUBECONFIG=/tmp/kubeconfig.tlnAhy
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

# Setup HPA for auto-scaling
make eks-setup-hpa EKS_NAMESPACE=$EKS_NAMESPACE

# Pre-warm to minimum replicas for 100 users
make eks-prewarm EKS_NAMESPACE=$EKS_NAMESPACE
```

### 2. Get Authentication Token

1. Open browser DevTools (F12)
2. Go to Application > Cookies
3. Copy the `session` or `auth_token` cookie value

### 3. Run Performance Test

```bash
# Get your product ID from the application
export BASE_URL="https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud"
export AUTH_TOKEN="your-token-here"
export PRODUCT_ID="your-product-uuid-here"

# Run test
make eks-performance-test \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BASE_URL=$BASE_URL \
  AUTH_TOKEN=$AUTH_TOKEN \
  PRODUCT_ID=$PRODUCT_ID
```

### 4. Monitor During Test

In another terminal:

```bash
# Watch pod scaling
watch -n 2 'kubectl get pods -n 20890-ideaforge-ai-dev-58a50 -l "app in (backend,frontend)"'

# Watch HPA
watch -n 2 'kubectl get hpa -n 20890-ideaforge-ai-dev-58a50'

# Watch resource usage
watch -n 2 'kubectl top pods -n 20890-ideaforge-ai-dev-58a50 -l "app in (backend,frontend)"'
```

## Expected Results

- **Backend pods**: Should scale from 5 to 10-15 during test
- **Frontend pods**: Should scale from 3 to 5-7 during test
- **P95 Response Time**: < 30 seconds ✅
- **Error Rate**: < 5% ✅
- **Throughput**: > 2 req/s ✅

## Troubleshooting

If pods don't scale:
```bash
# Check HPA status
kubectl describe hpa backend-hpa -n $EKS_NAMESPACE
kubectl describe hpa frontend-hpa -n $EKS_NAMESPACE

# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io
```

