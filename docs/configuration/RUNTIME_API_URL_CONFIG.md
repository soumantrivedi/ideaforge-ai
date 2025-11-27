# Runtime API URL Configuration

## Overview

The frontend now supports **runtime configuration** of the API URL via ConfigMap, eliminating the need to rebuild the Docker image when changing the API URL. This enables true cloud-native configuration management.

## How It Works

### 1. Runtime Configuration Injection

The entrypoint script (`scripts/docker-entrypoint.sh`) injects the API URL into `index.html` at container startup:

```html
<script>window.__API_URL__='${VITE_API_URL}';</script>
```

This script is injected before the closing `</head>` tag (or `</body>` if `</head>` doesn't exist).

### 2. Frontend Code

The frontend code uses `src/lib/runtime-config.ts` to read the API URL with the following priority:

1. **`window.__API_URL__`** (runtime injection from entrypoint script)
2. **`import.meta.env.VITE_API_URL`** (build-time fallback)
3. **Empty string** (for relative paths, nginx proxy)

### 3. Configuration Flow

```
ConfigMap (VITE_API_URL)
    ↓
Frontend Pod Environment Variable
    ↓
Entrypoint Script (docker-entrypoint.sh)
    ↓
Injected into index.html as window.__API_URL__
    ↓
Runtime Config Utility (runtime-config.ts)
    ↓
Frontend Application Code
```

## Configuration

### ConfigMap

The `VITE_API_URL` in the ConfigMap controls the API URL:

```yaml
# k8s/eks/configmap.yaml
data:
  VITE_API_URL: ""  # Empty = relative paths (nginx proxy)
  # OR
  VITE_API_URL: "https://api.example.com"  # Absolute URL
```

### Frontend Deployment

The frontend deployment reads `VITE_API_URL` from the ConfigMap:

```yaml
# k8s/eks/frontend.yaml
env:
  - name: VITE_API_URL
    valueFrom:
      configMapKeyRef:
        name: ideaforge-ai-config
        key: VITE_API_URL
```

## Usage in Code

### Using the Runtime Config Utility

All frontend files now use the runtime config utility:

```typescript
import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();
```

Or use the exported constant:

```typescript
import { API_URL } from '../lib/runtime-config';
```

### Updated Files

All frontend files have been updated to use the runtime config:
- `src/lib/api-client.ts`
- `src/contexts/AuthContext.tsx`
- `src/contexts/ThemeContext.tsx`
- All component files (30+ files)
- All service files

## Configuration Options

### Option 1: Relative Paths (Recommended for Cloud-Native)

Set `VITE_API_URL` to empty string in ConfigMap:

```yaml
VITE_API_URL: ""
```

The frontend will use relative paths like `/api/auth/login`, which are proxied by the frontend nginx to the backend service.

**Benefits:**
- No CORS issues (same origin)
- Works with service-to-service communication
- No need to know external URLs

### Option 2: Absolute URL

Set `VITE_API_URL` to the full backend URL:

```yaml
VITE_API_URL: "https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud"
```

**Use Cases:**
- Direct API access from browser
- Cross-domain scenarios
- Development/testing

## Updating Configuration

### Step 1: Update ConfigMap

```bash
kubectl edit configmap ideaforge-ai-config -n 20890-ideaforge-ai-dev-58a50
```

Or update the manifest and apply:

```bash
kubectl apply -f k8s/eks/configmap.yaml
```

### Step 2: Restart Frontend Pods

The entrypoint script runs at container startup, so restart the pods to pick up the new configuration:

```bash
kubectl rollout restart deployment/frontend -n 20890-ideaforge-ai-dev-58a50
```

### Step 3: Verify

Check that the API URL was injected correctly:

```bash
kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/frontend -- cat /usr/share/nginx/html/index.html | grep __API_URL__
```

You should see:
```html
<script>window.__API_URL__='YOUR_VALUE';</script>
```

## Benefits

1. **No Image Rebuild Required**: Change API URL via ConfigMap without rebuilding
2. **True Cloud-Native**: Configuration managed as Kubernetes resources
3. **Environment Flexibility**: Same image works across dev/staging/prod
4. **Quick Updates**: Change ConfigMap and restart pods (seconds, not minutes)
5. **Backward Compatible**: Still supports build-time `VITE_API_URL` as fallback

## Technical Details

### Entrypoint Script

The entrypoint script (`scripts/docker-entrypoint.sh`):
1. Reads `VITE_API_URL` from environment variable
2. Injects `<script>window.__API_URL__='${VITE_API_URL}';</script>` into `index.html`
3. Starts nginx

### Runtime Config Utility

The utility (`src/lib/runtime-config.ts`):
- Checks `window.__API_URL__` first (runtime)
- Falls back to `import.meta.env.VITE_API_URL` (build-time)
- Validates URL format
- Returns empty string for relative paths

### Dockerfile Changes

The Dockerfile now:
- Copies the entrypoint script
- Makes it executable
- Uses it as ENTRYPOINT

## Migration Notes

### From Build-Time to Runtime

If you have existing images built with `VITE_API_URL`:
1. The new runtime config will override build-time values
2. Update ConfigMap with desired value
3. Restart pods
4. No need to rebuild images

### Backward Compatibility

The solution maintains backward compatibility:
- Build-time `VITE_API_URL` still works as fallback
- Existing images continue to work
- Gradual migration possible

## Troubleshooting

### API URL Not Updating

1. **Check ConfigMap**: Verify `VITE_API_URL` is set correctly
   ```bash
   kubectl get configmap ideaforge-ai-config -n 20890-ideaforge-ai-dev-58a50 -o yaml | grep VITE_API_URL
   ```

2. **Check Pod Environment**: Verify pod has the env var
   ```bash
   kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/frontend -- env | grep VITE_API_URL
   ```

3. **Check Injected Script**: Verify injection in index.html
   ```bash
   kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/frontend -- cat /usr/share/nginx/html/index.html | grep __API_URL__
   ```

4. **Restart Pods**: Ensure pods were restarted after ConfigMap update
   ```bash
   kubectl rollout restart deployment/frontend -n 20890-ideaforge-ai-dev-58a50
   ```

### Browser Console Check

Open browser DevTools console and check:

```javascript
console.log(window.__API_URL__);
```

Should show the value from ConfigMap (or undefined if empty).

## Files Modified

- ✅ `src/lib/runtime-config.ts` - New runtime config utility
- ✅ `src/lib/api-client.ts` - Updated to use runtime config
- ✅ `scripts/docker-entrypoint.sh` - New entrypoint script
- ✅ `Dockerfile.frontend` - Updated to use entrypoint script
- ✅ All frontend component files (30+ files) - Updated to use runtime config
- ✅ `k8s/eks/frontend.yaml` - Already configured correctly (reads from ConfigMap)
- ✅ `k8s/eks/configmap.yaml` - Contains `VITE_API_URL`

## Summary

The frontend now supports runtime API URL configuration via ConfigMap, enabling:
- ✅ Configuration changes without image rebuilds
- ✅ True cloud-native configuration management
- ✅ Quick updates via ConfigMap changes
- ✅ Backward compatibility with build-time config

