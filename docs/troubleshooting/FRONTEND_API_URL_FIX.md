# Frontend API URL Configuration Issue

## Problem

The frontend is trying to connect to `localhost:8000/api/auth/login` instead of the backend API URL `https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`.

## Root Cause

Vite environment variables (prefixed with `VITE_`) are **build-time** variables, not runtime variables. This means:

1. The `VITE_API_URL` value is baked into the JavaScript bundle when the Docker image is built
2. Simply updating the ConfigMap and restarting pods **will not** change the API URL in the frontend
3. The frontend code falls back to `http://localhost:8000` when `VITE_API_URL` is not set or empty

## Current Status

✅ **ConfigMap Updated**: `VITE_API_URL` is now set to `https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
✅ **CORS Updated**: Backend CORS origins include the frontend domain
✅ **Backend Restarted**: Backend pods restarted to pick up new CORS settings

❌ **Frontend Image**: Still contains the old API URL (or fallback to localhost)

## Solution

The frontend Docker image needs to be **rebuilt** with the correct `VITE_API_URL` environment variable.

### Option 1: Rebuild Frontend Image (Recommended)

When building the frontend image, set the `VITE_API_URL` build argument:

```bash
docker build \
  --build-arg VITE_API_URL=https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud \
  -f Dockerfile.frontend \
  -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:NEW_TAG \
  .
```

Or update your CI/CD pipeline to use the correct API URL for EKS deployments.

### Option 2: Runtime Configuration (Code Change Required)

Modify the frontend code to support runtime API URL configuration:

1. Update `src/lib/api-client.ts` to check for a runtime configuration:
   ```typescript
   // Check for runtime config (set via window object or meta tag)
   const runtimeApiUrl = (window as any).__API_URL__ || 
                         document.querySelector('meta[name="api-url"]')?.getAttribute('content');
   
   const API_URL = runtimeApiUrl || 
                   import.meta.env.VITE_API_URL || 
                   'https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud';
   ```

2. Inject the API URL at runtime via an init script or nginx configuration

### Option 3: Use Relative Paths (If Same Domain)

If frontend and backend are on the same domain, use relative paths:
- Frontend: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
- Backend: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api`

This would require updating the ingress to route `/api/*` to the backend service.

## Immediate Workaround

Until the frontend is rebuilt, you can manually set the API URL in the browser console:

```javascript
// Open browser console on the frontend page and run:
localStorage.setItem('api_url', 'https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud');
// Then modify the frontend code to check localStorage for api_url
```

**Note**: This is a temporary workaround and requires code changes.

## Verification

After rebuilding the frontend:

1. Check the built JavaScript bundle contains the correct API URL:
   ```bash
   # In the frontend container
   grep -r "api-ideaforge-ai-dev-58a50" /usr/share/nginx/html/
   ```

2. Test the login functionality:
   - Open browser DevTools → Network tab
   - Attempt to login
   - Verify API calls go to `https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`

## Files Updated

- ✅ `k8s/eks/configmap.yaml` - Updated `VITE_API_URL` and `CORS_ORIGINS`
- ✅ ConfigMap applied to cluster
- ✅ Backend pods restarted

## Next Steps

1. **Rebuild frontend image** with correct `VITE_API_URL`
2. **Push new image** to registry
3. **Update deployment** to use new image tag
4. **Verify** login functionality works

