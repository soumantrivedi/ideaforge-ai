# Cloud-Native API Communication Fix

## Problem

Frontend was getting `ERR_CONNECTION_REFUSED` when trying to login because it was attempting to connect to `localhost:8000` instead of using the internal Kubernetes service.

## Solution: Cloud-Native Service-to-Service Communication

The frontend should use **relative paths** (`/api`) so that:
1. Browser makes request to frontend URL: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api/auth/login`
2. Request goes to frontend nginx (same origin)
3. Frontend nginx proxies `/api/*` to backend service internally: `http://backend:8000`
4. This uses Kubernetes DNS and service discovery (cloud-native pattern)

## Changes Made

### 1. Updated ConfigMap (`k8s/eks/configmap.yaml`)
```yaml
VITE_API_URL: ""  # Empty = use relative paths, nginx proxies to backend service
```

### 2. Updated Frontend Code (`src/lib/api-client.ts`)
```typescript
// Use relative path if VITE_API_URL is empty or not set (cloud-native pattern)
// Frontend nginx will proxy /api requests to backend service internally
const API_URL = import.meta.env.VITE_API_URL || '';
```

### 3. Frontend Nginx Configuration (Already Present)
The `nginx.conf` already has the proxy configuration:
```nginx
location /api {
    proxy_pass http://backend:8000;  # Uses Kubernetes service name
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Architecture

```
Browser Request
    ↓
https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud/api/auth/login
    ↓
NGINX Ingress Controller
    ↓
Frontend Service (ClusterIP)
    ↓
Frontend Pod (nginx on port 3000)
    ↓
nginx location /api proxy_pass
    ↓
Backend Service (ClusterIP) - http://backend:8000
    ↓
Backend Pod
```

## Important Note

**Vite environment variables are build-time**, so the frontend image needs to be **rebuilt** with the updated code and empty `VITE_API_URL` for this to take effect.

### Current Status
- ✅ ConfigMap updated
- ✅ Frontend code updated
- ✅ Frontend pods restarted
- ⚠️ **Frontend image needs rebuild** with new code (tag b5abec8 was built before this change)

### Next Steps

1. **Rebuild frontend image** with the updated code:
   ```bash
   docker build \
     --build-arg VITE_API_URL="" \
     -f Dockerfile.frontend \
     -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:NEW_TAG \
     .
   ```

2. **Push and deploy** the new image tag

3. **Verify** that frontend uses relative paths:
   - Open browser DevTools → Network tab
   - Attempt login
   - Verify API calls go to `/api/auth/login` (relative path)
   - Verify requests are proxied through frontend nginx to backend service

## Benefits of This Approach

1. **Cloud-Native**: Uses Kubernetes service discovery (`backend:8000`)
2. **No CORS Issues**: Same-origin requests (browser → frontend → backend)
3. **Internal Communication**: Backend service not exposed externally
4. **Simpler Configuration**: No need for external API URLs in frontend
5. **Security**: Backend only accessible through frontend proxy

## Verification

Test the proxy from inside a frontend pod:
```bash
kubectl exec -n 20890-ideaforge-ai-dev-58a50 <frontend-pod> -- \
  curl -s http://localhost:3000/api/health
```

This should return backend health status, confirming the proxy works.

