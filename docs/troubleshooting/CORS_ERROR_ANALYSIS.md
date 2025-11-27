# CORS Error Analysis and Fix

## Error Description

```
Access to fetch at 'http://localhost:8000/api/auth/login' from origin 'https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause Analysis

### Issue 1: Frontend Making Requests to localhost:8000
The frontend is trying to call `http://localhost:8000/api/auth/login` from the production domain. This happens because:

1. **Vite Environment Variables are Build-Time Only**
   - `VITE_API_URL` is baked into the JavaScript bundle when the Docker image is built
   - The frontend image `ghcr.io/soumantrivedi/ideaforge-ai/frontend:b5abec8` was built with `VITE_API_URL=http://localhost:8000` (default from `Dockerfile.frontend`)
   - Setting `VITE_API_URL=""` in the ConfigMap or pod environment variables **does not help** because the code is already compiled

2. **Hardcoded Fallback Values**
   - Many frontend files have fallback to `'http://localhost:8000'` when `VITE_API_URL` is empty/undefined:
     - `src/contexts/AuthContext.tsx`: `const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';`
     - `src/components/ProductChatInterface.tsx`: `const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';`
     - And 20+ other files

3. **Frontend Nginx Configuration**
   - The frontend nginx (`nginx.conf`) is correctly configured to proxy `/api` requests to `backend:8000`
   - However, the frontend code is making absolute URLs to `http://localhost:8000` instead of relative paths like `/api/auth/login`

### Issue 2: Backend CORS Configuration
The backend has incorrect CORS configuration:

1. **FRONTEND_URL is Hardcoded**
   - In `k8s/eks/backend.yaml`, `FRONTEND_URL` is hardcoded to `"https://ideaforge.ai"` instead of using the ConfigMap value
   - Should be: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`

2. **CORS_ORIGINS Not Passed to Backend**
   - The ConfigMap has `CORS_ORIGINS` set correctly, but it's not being passed to the backend pod as an environment variable
   - The backend reads `CORS_ORIGINS` from environment variables in `backend/main.py` line 265

## Fixes Applied

### 1. Backend Manifest Fix (`k8s/eks/backend.yaml`)
✅ **Fixed**: Updated `FRONTEND_URL` to use ConfigMap instead of hardcoded value
✅ **Fixed**: Added `CORS_ORIGINS` environment variable from ConfigMap

**Before:**
```yaml
- name: FRONTEND_URL
  value: "https://ideaforge.ai"  # Update with your frontend domain
```

**After:**
```yaml
- name: FRONTEND_URL
  valueFrom:
    configMapKeyRef:
      name: ideaforge-ai-config
      key: FRONTEND_URL
- name: CORS_ORIGINS
  valueFrom:
    configMapKeyRef:
      name: ideaforge-ai-config
      key: CORS_ORIGINS
```

### 2. Frontend Rebuild Required
⚠️ **ACTION REQUIRED**: The frontend Docker image needs to be rebuilt with `VITE_API_URL=""` (empty string)

**Build Command:**
```bash
docker build \
  --build-arg VITE_API_URL="" \
  -f Dockerfile.frontend \
  -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:latest \
  .
```

**Why This is Required:**
- Vite environment variables are **build-time only**
- The current image has `VITE_API_URL=http://localhost:8000` baked in
- Rebuilding with empty string will make the frontend use relative paths (`/api/...`)
- The frontend nginx will then proxy these requests to the backend service

### 3. Frontend Code Cleanup (Optional but Recommended)
To prevent future issues, consider updating all frontend files to use empty string fallback instead of `'http://localhost:8000'`:

**Current (Problematic):**
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**Recommended:**
```typescript
const API_URL = import.meta.env.VITE_API_URL || '';
```

This ensures that when `VITE_API_URL` is empty, the frontend uses relative paths which work correctly with the nginx proxy.

## Verification Steps

After applying the fixes:

1. **Apply Backend Manifest:**
   ```bash
   kubectl apply -f k8s/eks/backend.yaml
   kubectl rollout restart deployment/backend -n 20890-ideaforge-ai-dev-58a50
   ```

2. **Verify Backend Environment Variables:**
   ```bash
   kubectl exec -n 20890-ideaforge-ai-dev-58a50 deployment/backend -- env | grep -E "FRONTEND_URL|CORS_ORIGINS"
   ```

3. **Check Backend CORS Configuration:**
   ```bash
   kubectl logs -n 20890-ideaforge-ai-dev-58a50 deployment/backend | grep -i cors
   ```

4. **Rebuild and Deploy Frontend:**
   ```bash
   # Build with empty VITE_API_URL
   docker build --build-arg VITE_API_URL="" -f Dockerfile.frontend -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:NEW_TAG .
   
   # Push to registry
   docker push ghcr.io/soumantrivedi/ideaforge-ai/frontend:NEW_TAG
   
   # Update frontend.yaml with new image tag
   # Apply and restart
   kubectl apply -f k8s/eks/frontend.yaml
   kubectl rollout restart deployment/frontend -n 20890-ideaforge-ai-dev-58a50
   ```

5. **Test from Browser:**
   - Open browser console on `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
   - Try to login
   - Check Network tab - API calls should go to `/api/auth/login` (relative path) not `http://localhost:8000/api/auth/login`

## Summary

- ✅ **Backend CORS configuration fixed** - Now uses ConfigMap values
- ⚠️ **Frontend rebuild required** - Must rebuild with `VITE_API_URL=""` for production
- 📝 **Frontend code cleanup recommended** - Update fallback values to use empty string

The backend fix will resolve CORS issues once the frontend is rebuilt with the correct `VITE_API_URL`.

