# Environment-Specific URL Configuration Guide

This document explains how frontend and backend URLs are configured for different deployment environments.

## Overview

The application uses different URL configurations depending on the deployment environment:
- **docker-compose**: Direct container-to-container communication
- **kind cluster**: Ingress-based access with internal service proxying
- **eks cluster**: External domain access with internal service proxying

## Configuration Variables

### FRONTEND_URL

Used by the backend for CORS configuration. This should be the **external URL** that browsers use to access the frontend.

| Environment | Value | Notes |
|------------|-------|-------|
| docker-compose | `http://localhost:3001` | Frontend exposed on port 3001 |
| kind | `http://localhost:80` or `http://ideaforge.local` | Via ingress controller |
| eks | `https://your-domain.cf.platform.mckinsey.cloud` | External domain |

### VITE_API_URL

Used at **build-time** to configure the frontend API client. This is baked into the JavaScript bundle.

| Environment | Value | Notes |
|------------|-------|-------|
| docker-compose | `http://localhost:8000` | Direct backend access |
| kind | `""` (empty) | Relative paths, nginx proxies to backend |
| eks | `""` (empty) | Relative paths, nginx proxies to backend |

**Important**: For kind/eks, use empty string to enable cloud-native service-to-service communication via nginx proxy.

## File Locations

### Environment Files

- **`.env.example`**: Template with environment-specific comments
- **`.env`**: Your local configuration (gitignored)

### Kubernetes ConfigMaps

- **`k8s/base/configmap.yaml`**: Base configuration
- **`k8s/kind/configmap.yaml`**: Kind cluster configuration
- **`k8s/eks/configmap.yaml`**: EKS cluster configuration

### Docker Configuration

- **`docker-compose.yml`**: Docker Compose environment variables
- **`Dockerfile.frontend`**: Frontend build arguments

### Backend Configuration

- **`backend/config.py`**: Default values and environment variable loading
- **`backend/main.py`**: CORS origins configuration

## How It Works

### Docker Compose

```
Browser → http://localhost:3001 → Frontend Container
Browser → http://localhost:8000 → Backend Container (direct)
```

Frontend makes direct API calls to `http://localhost:8000`.

### Kind/EKS (Cloud-Native)

```
Browser → Ingress → Frontend Service → Frontend Pod (nginx)
                                    ↓
                            nginx location /api
                                    ↓
                            Backend Service → Backend Pod
```

Frontend uses relative paths (`/api`), nginx proxies to `http://backend:8000` internally.

## Migration Notes

### From docker-compose to Kubernetes

1. **VITE_API_URL**: Change from `http://localhost:8000` to `""` (empty)
2. **FRONTEND_URL**: Change from `http://localhost:3001` to ingress URL
3. **Rebuild frontend image**: Required because VITE_API_URL is build-time

### Updating Existing Deployments

1. Update ConfigMap with new values
2. Rebuild frontend image with correct `VITE_API_URL`
3. Restart pods to pick up ConfigMap changes
4. Verify CORS and API connectivity

## Verification

### Check Current Configuration

```bash
# Docker Compose
docker-compose config | grep -E "FRONTEND_URL|VITE_API_URL"

# Kind
kubectl get configmap ideaforge-ai-config -n ideaforge-ai -o yaml | grep -E "FRONTEND_URL|VITE_API_URL"

# EKS
kubectl get configmap ideaforge-ai-config -n <namespace> -o yaml | grep -E "FRONTEND_URL|VITE_API_URL"
```

### Test API Connectivity

```bash
# Docker Compose
curl http://localhost:8000/health

# Kind (via ingress)
curl http://localhost:80/api/health

# EKS (via external domain)
curl https://api-your-domain.cf.platform.mckinsey.cloud/health
```

## Troubleshooting

### CORS Errors

- Verify `FRONTEND_URL` matches the actual frontend URL
- Check `CORS_ORIGINS` includes the frontend URL
- Restart backend pods after ConfigMap changes

### API Connection Refused

- For docker-compose: Check backend is running on port 8000
- For kind/eks: Verify nginx proxy configuration
- Check frontend image was built with correct `VITE_API_URL`

### Build-Time vs Runtime

Remember: `VITE_API_URL` is **build-time**, not runtime. Changing ConfigMap won't update the frontend API URL unless you rebuild the image.

