# Async Job Processing Configuration

## Overview

The async job processing system now supports configurable polling intervals and timeouts via Kubernetes ConfigMap. This allows you to adjust the polling behavior without rebuilding the frontend image, which is essential for managing load with 400+ concurrent users.

## Configuration Options

All configuration is done via the `ideaforge-ai-config` ConfigMap:

### `JOB_POLL_INTERVAL_MS`
- **Description**: Polling interval in milliseconds
- **Default**: `5000` (5 seconds)
- **Purpose**: Controls how often the frontend polls for job status
- **Recommendation**: 
  - For 400+ concurrent users: `5000-10000` (5-10 seconds)
  - For lower load: `2000-3000` (2-3 seconds)
  - Higher values reduce network load but increase perceived response time

### `JOB_MAX_POLL_ATTEMPTS`
- **Description**: Maximum number of polling attempts
- **Default**: `120` (10 minutes at 5s intervals)
- **Purpose**: Prevents infinite polling
- **Calculation**: `max_poll_attempts * poll_interval_ms = total_timeout`
  - Default: `120 * 5000ms = 600000ms = 10 minutes`

### `JOB_TIMEOUT_MS`
- **Description**: Overall job timeout in milliseconds
- **Default**: `600000` (10 minutes)
- **Purpose**: Absolute timeout for job processing
- **Note**: Should be >= `max_poll_attempts * poll_interval_ms`

## Example ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ideaforge-ai-config
  namespace: 20890-ideaforge-ai-dev-58a50
data:
  JOB_POLL_INTERVAL_MS: "5000"      # 5 seconds
  JOB_MAX_POLL_ATTEMPTS: "120"      # 120 attempts
  JOB_TIMEOUT_MS: "600000"          # 10 minutes
```

## How It Works

1. **ConfigMap** stores the configuration values
2. **Frontend Deployment** reads values as environment variables
3. **Docker Entrypoint Script** injects values into HTML as `window.__JOB_*__`
4. **Frontend Code** reads from `window` object or uses defaults
5. **Async Job Processor** uses the configured values for polling

## Updating Configuration

### Option 1: Update ConfigMap Directly

```bash
kubectl edit configmap ideaforge-ai-config -n 20890-ideaforge-ai-dev-58a50
```

Add or update:
```yaml
data:
  JOB_POLL_INTERVAL_MS: "10000"     # 10 seconds for high load
  JOB_MAX_POLL_ATTEMPTS: "60"       # 10 minutes at 10s intervals
  JOB_TIMEOUT_MS: "600000"          # 10 minutes
```

### Option 2: Apply Updated ConfigMap

```bash
kubectl apply -f k8s/eks/configmap.yaml
```

### Restart Frontend Pods

After updating the ConfigMap, restart frontend pods to pick up new values:

```bash
kubectl rollout restart deployment/frontend -n 20890-ideaforge-ai-dev-58a50
```

## Load Management Recommendations

### For 400+ Concurrent Users

```yaml
JOB_POLL_INTERVAL_MS: "10000"       # 10 seconds - reduces polling by 80%
JOB_MAX_POLL_ATTEMPTS: "60"         # 10 minutes total
JOB_TIMEOUT_MS: "600000"            # 10 minutes
```

**Impact**: 
- Reduces polling requests by 80% (from 2s to 10s intervals)
- For 400 users: ~40 requests/second instead of ~200 requests/second
- Still completes within 10 minutes

### For Lower Load (< 100 users)

```yaml
JOB_POLL_INTERVAL_MS: "3000"        # 3 seconds
JOB_MAX_POLL_ATTEMPTS: "200"        # 10 minutes total
JOB_TIMEOUT_MS: "600000"            # 10 minutes
```

## Datetime Serialization Fix

The datetime serialization error (`Object of type datetime is not JSON serializable`) has been fixed by:

1. Using Pydantic `field_serializer` to serialize datetime fields to ISO format strings
2. Applied to both `JobStatusResponse` and `JobResultResponse` models
3. Ensures consistent JSON serialization across all endpoints

## Monitoring

### Check Current Configuration

```bash
kubectl get configmap ideaforge-ai-config -n 20890-ideaforge-ai-dev-58a50 -o yaml | grep JOB_
```

### Monitor Polling Load

```bash
# Check backend logs for polling frequency
kubectl logs -n 20890-ideaforge-ai-dev-58a50 -l app=backend | grep "GET /api/multi-agent/jobs" | wc -l

# Check Redis for active jobs
kubectl exec -n 20890-ideaforge-ai-dev-58a50 -it deployment/redis -- redis-cli KEYS "job:*" | wc -l
```

## Troubleshooting

### Polling Too Frequent

If you see high network load:
1. Increase `JOB_POLL_INTERVAL_MS` to 10000 (10 seconds)
2. Restart frontend pods
3. Monitor backend logs for reduced request frequency

### Jobs Timing Out

If jobs are timing out:
1. Increase `JOB_TIMEOUT_MS` to allow longer processing
2. Increase `JOB_MAX_POLL_ATTEMPTS` proportionally
3. Ensure `JOB_TIMEOUT_MS >= JOB_MAX_POLL_ATTEMPTS * JOB_POLL_INTERVAL_MS`

### Datetime Serialization Errors

If you still see datetime errors:
1. Verify backend is using the latest image with `field_serializer`
2. Check backend logs for serialization errors
3. Ensure Pydantic version supports `field_serializer` (v2+)

## Files Modified

- `k8s/eks/configmap.yaml` - Added job configuration
- `k8s/eks/frontend.yaml` - Added environment variables
- `scripts/docker-entrypoint.sh` - Inject job config into HTML
- `src/lib/job-config.ts` - Read config from runtime
- `src/components/MainApp.tsx` - Use configurable values
- `backend/models/schemas.py` - Fix datetime serialization

