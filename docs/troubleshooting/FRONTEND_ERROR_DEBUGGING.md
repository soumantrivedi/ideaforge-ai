# Frontend Error Debugging Guide

## Understanding Minified JavaScript Errors

When you see errors like:
```
ut @ index-twq0XTQ5.js:40
u @ index-twq0XTQ5.js:40
m @ index-twq0XTQ5.js:395
...
```

These are from **minified/bundled JavaScript** files, which makes debugging difficult. Here's how to debug them:

## Steps to Debug

### 1. Check Browser Console for Full Error Message

The stack trace alone doesn't show the actual error. Look for:
- **Red error messages** above the stack trace
- **Network errors** in the Network tab
- **Console warnings** that might give context

### 2. Check Network Tab

1. Open DevTools (F12 or Cmd+Option+I)
2. Go to **Network** tab
3. Look for failed requests (red status codes)
4. Check:
   - **500 errors** - Backend server errors
   - **401 errors** - Authentication issues
   - **404 errors** - Missing endpoints
   - **CORS errors** - Cross-origin issues

### 3. Common Causes

#### API Connection Issues
- **Backend not responding**: Check if backend pods are running
- **Wrong API URL**: Verify `VITE_API_URL` in ConfigMap
- **CORS errors**: Check backend CORS configuration

#### Authentication Issues
- **Token expired**: Check localStorage for `auth_token`
- **401 errors**: Session expired, need to re-login
- **Missing user data**: Check if user info API call is failing

#### React Component Errors
- **Unhandled promise rejections**: API calls not wrapped in try/catch
- **State updates after unmount**: Components updating after being removed
- **Missing error boundaries**: Errors crashing the entire app

### 4. Enable Source Maps (Development)

If you're running in development mode, source maps should show original file names and line numbers instead of minified code.

### 5. Check Backend Logs

```bash
# Check backend pod logs
kubectl logs -n ideaforge-ai -l app=backend --tail=100

# Check for specific errors
kubectl logs -n ideaforge-ai -l app=backend | grep -i "error\|exception\|500"
```

### 6. Check Frontend Logs

```bash
# Check frontend pod logs
kubectl logs -n ideaforge-ai -l app=frontend --tail=100
```

### 7. Verify Environment Configuration

```bash
# Check ConfigMap
kubectl get configmap ideaforge-ai-config -n ideaforge-ai -o yaml

# Check Secrets
kubectl get secret ideaforge-ai-secrets -n ideaforge-ai -o yaml
```

## Error Boundary Added

An `ErrorBoundary` component has been added to catch React errors and display a user-friendly error message instead of a blank screen.

The error boundary will:
- Catch React component errors
- Display a helpful error message
- Show error details for debugging
- Provide "Try Again" and "Reload Page" buttons

## Global Error Handlers

Global error handlers have been added to catch:
- Unhandled JavaScript errors
- Unhandled promise rejections

These will log errors to the console for debugging.

## Next Steps

1. **Rebuild and redeploy** the frontend to include the ErrorBoundary
2. **Check the browser console** for the actual error message (not just the stack trace)
3. **Check the Network tab** for failed API requests
4. **Check backend logs** for server-side errors
5. **Verify API keys** are properly loaded (we fixed the secret loading issue)

## Rebuilding Frontend

After making changes, rebuild and redeploy:

```bash
# Rebuild frontend image
make build-apps

# Load into kind cluster
make kind-load-images

# Update deployment
make kind-update-images

# Restart pods
kubectl rollout restart deployment/frontend -n ideaforge-ai
```

