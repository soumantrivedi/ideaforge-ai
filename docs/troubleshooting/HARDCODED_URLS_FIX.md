# Hardcoded URLs Removal

**Date:** November 30, 2025  
**Status:** ✅ Fixed

---

## Issue

The codebase had hardcoded `localhost:8080` and `localhost:8081` URLs in the backend CORS configuration, which would cause issues in production deployments where these URLs don't exist.

---

## Changes Made

### 1. ✅ Backend CORS Configuration (`backend/main.py`)

**Before:**
```python
cors_origins = [
    settings.frontend_url,
    "http://localhost:3000",  # Vite dev server
    "http://localhost:3001",  # docker-compose frontend
    "http://localhost:5173",  # Vite HMR port
    "http://localhost",  # For ingress access (port 80)
    "http://localhost:80",  # Explicit port 80
    "http://localhost:8080",  # For kind cluster with port 8080
    "http://ideaforge.local",  # For hostname-based access
    "http://api.ideaforge.local",  # For API hostname
]
```

**After:**
```python
# Build CORS allowed origins list
# Origins are configured via:
# 1. FRONTEND_URL environment variable (via settings.frontend_url)
# 2. CORS_ORIGINS environment variable (comma-separated list)
# No hardcoded URLs - all origins must be explicitly configured via environment variables
cors_origins = []

# Add frontend URL from settings (if configured)
if settings.frontend_url:
    cors_origins.append(settings.frontend_url)

# Add origins from CORS_ORIGINS environment variable (comma-separated)
import os
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins.extend([origin.strip() for origin in env_origins if origin.strip()])

# Remove duplicates and empty strings
cors_origins = list(set([origin for origin in cors_origins if origin]))
```

**Benefits:**
- ✅ No hardcoded URLs in application code
- ✅ All CORS origins must be explicitly configured via environment variables
- ✅ Production-ready - works with any domain/port configuration
- ✅ Added logging to warn if no CORS origins are configured

---

### 2. ✅ Verification Script (`scripts/verify-deployment.sh`)

**Updated to use environment variables:**
```bash
NAMESPACE="${K8S_NAMESPACE:-ideaforge-ai}"
CONTEXT="${K8S_CONTEXT:-kind-ideaforge-ai}"
INGRESS_PORT="${INGRESS_PORT:-8081}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-8000}"
```

**Benefits:**
- ✅ Scripts can be configured via environment variables
- ✅ Defaults provided for local development
- ✅ Production deployments can override via environment variables

---

## Configuration

### For Local Development

Set in `.env` or `env.kind`:
```bash
FRONTEND_URL=http://localhost:8080
CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:8080,http://ideaforge.local
```

### For Production (EKS)

Set in ConfigMap or environment variables:
```bash
FRONTEND_URL=https://your-production-domain.com
CORS_ORIGINS=https://your-production-domain.com,https://api.your-production-domain.com
```

---

## Files Changed

1. ✅ `backend/main.py` - Removed hardcoded CORS origins
2. ✅ `scripts/verify-deployment.sh` - Made URLs configurable via environment variables

---

## Files NOT Changed (Intentionally)

The following files contain `localhost` URLs but are **configuration files** that should be customized per environment:

- `k8s/kind/configmap.yaml` - Local development configuration
- `k8s/eks/configmap.yaml` - Production configuration
- `env.kind.example` - Example configuration
- `env.eks.example` - Example configuration

These are **meant to be customized** and are not hardcoded in application code.

---

## Verification

### Check CORS Configuration

```bash
# Check backend logs for CORS origins
kubectl logs -n ideaforge-ai --context kind-ideaforge-ai -l app=backend | grep cors_origins
```

### Test CORS

```bash
# From browser console or curl
curl -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://your-backend-url/api/auth/login
```

---

## Summary

✅ **All hardcoded URLs removed from application code**  
✅ **CORS origins now fully configurable via environment variables**  
✅ **Production-ready - no localhost dependencies in code**  
✅ **Scripts use environment variables with sensible defaults**

The application now relies entirely on environment-based configuration, making it suitable for any deployment environment without code changes.

