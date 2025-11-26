# Platform-Specific Environment Configuration Guide

This guide explains how to configure environment variables for different deployment platforms using Kustomize.

## Overview

The application uses a **platform-specific environment configuration** approach:

- **Common variables**: Stored in `env.example` (root level)
- **Platform-specific variables**: Stored in platform-specific env files
  - `env.eks.example` → Production (EKS)
  - `env.kind.example` → Local Development (Kind)
  - `env.docker-compose.example` → Fallback (Docker Compose)

## File Structure

```
.
├── env.example                    # Common variables (shared across all platforms)
├── env.eks.example               # EKS production-specific variables
├── env.kind.example              # Kind local development-specific variables
├── env.docker-compose.example    # Docker Compose fallback-specific variables
└── k8s/
    ├── base/
    │   └── configmap.yaml        # Base ConfigMap (common values only)
    └── overlays/
        ├── eks/
        │   ├── kustomization.yaml
        │   └── configmap-env.yaml  # EKS-specific ConfigMap overrides
        └── kind/
            ├── kustomization.yaml
            └── configmap-env.yaml  # Kind-specific ConfigMap overrides
```

## Setup Instructions

### 1. Copy Example Files

```bash
# Copy common env file
cp env.example .env

# Copy platform-specific env files
cp env.eks.example env.eks
cp env.kind.example env.kind
cp env.docker-compose.example env.docker-compose
```

### 2. Configure Platform-Specific Variables

#### For EKS (Production)

Edit `env.eks`:

```bash
# Database password (use strong password)
POSTGRES_PASSWORD=your-strong-production-password

# Frontend URL (external domain)
FRONTEND_URL=https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud

# CORS origins (include all domains)
CORS_ORIGINS=https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud,https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud

# Namespace
K8S_NAMESPACE=20890-ideaforge-ai-dev-58a50
```

#### For Kind (Local Development)

Edit `env.kind`:

```bash
# Database password (dev password is fine)
POSTGRES_PASSWORD=devpassword

# Frontend URL (via ingress)
FRONTEND_URL=http://localhost:80

# CORS origins (local development)
CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:8080,http://ideaforge.local

# Namespace
K8S_NAMESPACE=ideaforge-ai
```

#### For Docker Compose (Fallback)

Edit `env.docker-compose` or copy to `.env`:

```bash
# Database password
POSTGRES_PASSWORD=devpassword

# Direct backend access (no nginx proxy)
VITE_API_URL=http://localhost:8000

# Frontend URL (exposed on port 3001)
FRONTEND_URL=http://localhost:3001
```

## Loading Configuration

### Using Kustomize (Recommended)

Kustomize automatically merges platform-specific ConfigMaps:

```bash
# For Kind
kubectl apply -k k8s/overlays/kind

# For EKS
kubectl apply -k k8s/overlays/eks
```

### Using Helper Script

```bash
# Load from env.kind
./k8s/scripts/load-config-from-env.sh kind

# Load from env.eks (with namespace)
./k8s/scripts/load-config-from-env.sh eks 20890-ideaforge-ai-dev-58a50
```

### Manual ConfigMap Update

```bash
# Extract variables and create ConfigMap
kubectl create configmap ideaforge-ai-config \
  --from-env-file=env.kind \
  --namespace=ideaforge-ai \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Platform-Specific Variables

### Common Variables (env.example)

These are shared across all platforms:
- Database configuration (host, port, user, db name)
- Redis URL
- AI provider API keys
- Integration tokens
- Agent model configuration
- Feature flags
- MCP server URLs

### EKS-Specific (env.eks)

- `POSTGRES_PASSWORD`: Strong production password
- `VITE_API_URL`: Empty (relative paths, nginx proxy)
- `FRONTEND_URL`: External domain URL
- `CORS_ORIGINS`: Production domains
- `K8S_NAMESPACE`: EKS namespace

### Kind-Specific (env.kind)

- `POSTGRES_PASSWORD`: Dev password
- `VITE_API_URL`: Empty (relative paths, nginx proxy)
- `FRONTEND_URL`: Ingress URL (localhost:80)
- `CORS_ORIGINS`: Local development origins
- `K8S_NAMESPACE`: Kind namespace (ideaforge-ai)

### Docker Compose-Specific (env.docker-compose)

- `POSTGRES_PASSWORD`: Dev password
- `DATABASE_URL`: Full database connection string
- `VITE_API_URL`: Direct backend URL (http://localhost:8000)
- `FRONTEND_URL`: Frontend URL (http://localhost:3001)
- `CORS_ORIGINS`: Local development origins

## Kustomize Overlays

### Base (k8s/base/)

Contains common Kubernetes resources with base configuration.

### EKS Overlay (k8s/overlays/eks/)

- Merges EKS-specific ConfigMap via `configmap-env.yaml`
- Applies EKS patches for postgres, redis, ingress
- Sets EKS-specific image tags

### Kind Overlay (k8s/overlays/kind/)

- Merges Kind-specific ConfigMap via `configmap-env.yaml`
- Sets Kind-specific image tags (local images)
- Uses `imagePullPolicy: Never` for local images

## Best Practices

1. **Never commit actual env files**: Only commit `.example` files
2. **Use strong passwords in production**: EKS should use strong `POSTGRES_PASSWORD`
3. **Keep common vars in sync**: Update `env.example` when adding new common variables
4. **Platform-specific overrides**: Only override what's different per platform
5. **Use Kustomize**: Prefer kustomize overlays over manual ConfigMap updates

## Troubleshooting

### ConfigMap Not Updating

```bash
# Check current ConfigMap
kubectl get configmap ideaforge-ai-config -n <namespace> -o yaml

# Force update
kubectl delete configmap ideaforge-ai-config -n <namespace>
kubectl apply -k k8s/overlays/<platform>
```

### Wrong Values in Pods

```bash
# Restart pods to pick up new ConfigMap
kubectl rollout restart deployment/backend -n <namespace>
kubectl rollout restart deployment/frontend -n <namespace>
```

### Kustomize Build Issues

```bash
# Preview what kustomize will generate
kubectl kustomize k8s/overlays/<platform>

# Check for errors
kubectl kustomize k8s/overlays/<platform> --validate
```

## Migration from Old Structure

If you're migrating from the old single `env.example` approach:

1. Copy your existing `.env` values to appropriate platform files
2. Extract common values to `env.example`
3. Update platform-specific values in `env.<platform>`
4. Test with `kubectl kustomize` before applying

