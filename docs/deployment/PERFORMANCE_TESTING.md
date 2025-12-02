# Performance Testing Guide for 100 Concurrent Users

This guide explains how to pre-warm the EKS production environment and run performance tests with 100 concurrent users.

## Pre-Warming Setup

### 1. Apply HPA (Horizontal Pod Autoscaler)

The HPA automatically scales pods based on CPU and memory usage:

```bash
# Apply HPA configurations
kubectl apply -f k8s/eks/hpa-backend.yaml
kubectl apply -f k8s/eks/hpa-frontend.yaml

# Verify HPA status
kubectl get hpa -n 20890-ideaforge-ai-dev-58a50
```

### 2. Update Resource Limits

The deployment manifests have been updated with increased resources:
- **Backend**: 1.5Gi-3Gi memory, 1-3 CPU cores (scales 5-20 replicas)
- **Frontend**: 256Mi-512Mi memory, 100m-500m CPU (scales 3-10 replicas)

### 3. Pre-Warm Deployments

```bash
# Scale to minimum replicas for 100 users
kubectl scale deployment backend -n 20890-ideaforge-ai-dev-58a50 --replicas=5
kubectl scale deployment frontend -n 20890-ideaforge-ai-dev-58a50 --replicas=3

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=backend -n 20890-ideaforge-ai-dev-58a50 --timeout=300s
kubectl wait --for=condition=ready pod -l app=frontend -n 20890-ideaforge-ai-dev-58a50 --timeout=300s
```

## Running Performance Tests

### Prerequisites

```bash
# Install dependencies
pip install -r scripts/performance-test-requirements.txt
```

### Basic Test

```bash
python3 scripts/performance-test.py \
  --url https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud \
  --token YOUR_AUTH_TOKEN \
  --product-id YOUR_PRODUCT_ID \
  --users 100 \
  --ramp-up 30
```

### Advanced Test with Metrics Export

```bash
python3 scripts/performance-test.py \
  --url https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud \
  --token YOUR_AUTH_TOKEN \
  --product-id YOUR_PRODUCT_ID \
  --users 100 \
  --ramp-up 30 \
  --output performance-metrics-$(date +%Y%m%d-%H%M%S).json
```

### Parameters

- `--url`: Base URL of the application
- `--token`: Authentication token (get from browser DevTools > Application > Cookies)
- `--product-id`: Product ID to use for testing
- `--users`: Number of concurrent users (default: 100)
- `--ramp-up`: Ramp-up time in seconds (default: 30)
- `--output`: Optional JSON file to save metrics

## NFR (Non-Functional Requirements) Targets

The test automatically validates these NFR targets:

1. **Response Time (P95)**: < 30 seconds
2. **Error Rate**: < 5%
3. **Throughput**: > 2 requests/second
4. **Quality Score**: > 60/100
5. **First Chunk Time (TTFB)**: < 5 seconds

## Monitoring During Tests

### Watch Pod Scaling

```bash
# Watch backend pods
watch -n 2 'kubectl get pods -n 20890-ideaforge-ai-dev-58a50 -l app=backend'

# Watch frontend pods
watch -n 2 'kubectl get pods -n 20890-ideaforge-ai-dev-58a50 -l app=frontend'

# Watch HPA
watch -n 2 'kubectl get hpa -n 20890-ideaforge-ai-dev-58a50'
```

### Monitor Resource Usage

```bash
# Backend resource usage
kubectl top pods -n 20890-ideaforge-ai-dev-58a50 -l app=backend

# Frontend resource usage
kubectl top pods -n 20890-ideaforge-ai-dev-58a50 -l app=frontend
```

### Check Logs

```bash
# Backend logs
kubectl logs -f -n 20890-ideaforge-ai-dev-58a50 -l app=backend --tail=100

# Check for errors
kubectl logs -n 20890-ideaforge-ai-dev-58a50 -l app=backend | grep -i error | tail -20
```

## Expected Results for 100 Users

### Resource Scaling

- **Backend Pods**: Should scale from 5 to 10-15 during peak load
- **Frontend Pods**: Should scale from 3 to 5-7 during peak load
- **CPU Usage**: Should stay below 70% average (triggers scaling)
- **Memory Usage**: Should stay below 80% average (triggers scaling)

### Performance Metrics

- **Average Response Time**: 15-25 seconds (agent processing)
- **P95 Response Time**: < 30 seconds
- **Throughput**: 3-5 requests/second
- **Error Rate**: < 2%
- **First Chunk Time**: 2-4 seconds

## Troubleshooting

### High Error Rate

1. Check database connection pool:
   ```bash
   kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/postgres -- psql -U agentic_pm -d agentic_pm_db -c "SHOW max_connections;"
   ```

2. Check Redis connections:
   ```bash
   kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/redis -- redis-cli INFO clients
   ```

3. Review backend logs for rate limiting or API key issues

### Slow Response Times

1. Check if pods are scaling properly:
   ```bash
   kubectl get hpa -n 20890-ideaforge-ai-dev-58a50
   ```

2. Check for resource constraints:
   ```bash
   kubectl describe nodes | grep -A 5 "Allocated resources"
   ```

3. Review agent processing times in logs

### Pods Not Scaling

1. Verify HPA is configured:
   ```bash
   kubectl describe hpa backend-hpa -n 20890-ideaforge-ai-dev-58a50
   ```

2. Check metrics server:
   ```bash
   kubectl get apiservice v1beta1.metrics.k8s.io
   ```

3. Verify resource requests/limits are set correctly

## Post-Test Cleanup

After testing, you can scale down to save resources:

```bash
# Scale down to minimum
kubectl scale deployment backend -n 20890-ideaforge-ai-dev-58a50 --replicas=2
kubectl scale deployment frontend -n 20890-ideaforge-ai-dev-58a50 --replicas=2
```

Or let HPA manage scaling automatically (recommended for production).

