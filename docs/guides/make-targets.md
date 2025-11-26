# Make Targets Reference

Complete reference for all `make` targets available in IdeaForge AI.

## Quick Reference

```bash
# Show all available targets
make help

# Show current version
make version
```

## Development Workflow

### Building Images

```bash
# Build all images (with cache)
make build

# Build without cache (clean build)
make build-no-cache

# Build only application images (backend + frontend)
make build-apps
```

### Docker Compose

```bash
# Start all services
make up

# Stop services (preserves data)
make down

# Restart services
make restart

# View logs
make logs SERVICE=backend
make logs-all

# Check health
make health

# Rebuild and restart (preserves database)
make rebuild
```

### Database Management

```bash
# Backup database
make db-backup

# Restore from backup
make db-restore BACKUP=backups/backup_file.sql

# List available backups
make db-list-backups

# Run migrations
make db-migrate

# Seed database
make db-seed

# Complete setup (migrations + seed)
make db-setup

# Open PostgreSQL shell
make db-shell
```

### Complete Setup

```bash
# Full deployment (build + start + migrations + health check)
make deploy

# Full deployment with complete setup (build + start + migrations + seed + agno init)
make deploy-full

# Complete setup (migrations + seed + agno init)
make setup
```

## Kind Cluster (Local Development)

### Cluster Management

```bash
# Create kind cluster
make kind-create

# Delete kind cluster
make kind-delete

# Install NGINX ingress
make kind-setup-ingress
```

### Image Management

```bash
# Load Docker images into kind
make kind-load-images

# Update image references in manifests
make kind-update-images
```

### Deployment

```bash
# Full deployment (creates cluster, installs ingress, loads images, deploys)
make kind-deploy

# Internal deployment (assumes cluster exists and images are loaded)
make kind-deploy-internal

# Rebuild and deploy to kind
make rebuild-and-deploy-kind
```

### Secrets and Configuration

```bash
# Load secrets from .env file
make kind-load-secrets

# Create database ConfigMaps
make kind-create-db-configmaps

# Update database ConfigMaps
make kind-update-db-configmaps
```

### Verification and Testing

```bash
# Show cluster status
make kind-status

# Test service-to-service interactions
make kind-test

# View logs
make kind-logs

# Port forward for local access
make kind-port-forward
```

### Agno Initialization

```bash
# Initialize Agno framework in kind cluster
make kind-agno-init
```

### Cleanup

```bash
# Clean up deployment (keeps cluster)
make kind-cleanup
```

## EKS Production Deployment

### Prerequisites

```bash
# Setup GitHub Container Registry secret
make eks-setup-ghcr-secret EKS_NAMESPACE=your-namespace

# Load secrets from .env file
make eks-load-secrets EKS_NAMESPACE=your-namespace
```

### Deployment

```bash
# Full EKS deployment
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=tag \
  FRONTEND_IMAGE_TAG=tag

# Deploy to EKS (assumes secrets are loaded)
make eks-deploy \
  EKS_NAMESPACE=your-namespace \
  BACKEND_IMAGE_TAG=tag \
  FRONTEND_IMAGE_TAG=tag
```

### Verification

```bash
# Show EKS cluster status
make eks-status EKS_NAMESPACE=your-namespace

# Test service-to-service interactions
make eks-test EKS_NAMESPACE=your-namespace

# Port forward for local access
make eks-port-forward EKS_NAMESPACE=your-namespace
```

### Configuration

```bash
# Update database ConfigMaps
make eks-update-db-configmaps EKS_NAMESPACE=your-namespace

# Add demo accounts
make eks-add-demo-accounts EKS_NAMESPACE=your-namespace
```

### Agno Initialization

```bash
# Initialize Agno framework in EKS
make eks-agno-init EKS_NAMESPACE=your-namespace
```

## Error Checking

```bash
# Check for errors in all services
make check-errors

# Check specific service
make check-errors-backend
make check-errors-frontend
make check-errors-postgres
make check-errors-redis

# Comprehensive error check
make check-all-errors
```

## Logs

```bash
# View all service logs
make check-logs

# View specific service logs
make check-logs-backend
make check-logs-frontend
make check-logs-postgres
make check-logs-redis
```

## Safe Operations

### Rebuild with Data Preservation

```bash
# Safe rebuild (backup DB, rebuild images, restore if needed)
make rebuild-safe
```

### Cleanup with Backup

```bash
# Complete cleanup (backup DB first)
make clean-all
```

### Migration

```bash
# Migrate database from docker-compose to kind
make migrate-to-kind
```

## Container Access

```bash
# Open shell in backend container
make shell-backend

# Open shell in frontend container
make shell-frontend
```

## Common Workflows

### Local Development (Kind)

```bash
# 1. Build images
make build-apps

# 2. Deploy to kind
make kind-deploy

# 3. Check status
make kind-status

# 4. Test
make kind-test
```

### Production Deployment (EKS)

```bash
# 1. Setup secrets
make eks-setup-ghcr-secret EKS_NAMESPACE=your-namespace
make eks-load-secrets EKS_NAMESPACE=your-namespace

# 2. Deploy
make eks-deploy-full \
  EKS_NAMESPACE=your-namespace \
  BACKEND_IMAGE_TAG=tag \
  FRONTEND_IMAGE_TAG=tag

# 3. Verify
make eks-status EKS_NAMESPACE=your-namespace
```

### Rebuild and Redeploy

```bash
# Docker Compose
make rebuild-and-deploy

# Kind Cluster
make rebuild-and-deploy-kind
```

## Environment Variables

Make targets use these environment variables:

- `GIT_SHA`: Automatically set from git
- `VERSION`: Same as GIT_SHA
- `IMAGE_TAG`: ideaforge-ai-$(VERSION)
- `K8S_NAMESPACE`: Default: ideaforge-ai
- `KIND_CLUSTER_NAME`: Default: ideaforge-ai
- `EKS_NAMESPACE`: Required for EKS operations
- `BACKEND_IMAGE_TAG`: Backend image tag
- `FRONTEND_IMAGE_TAG`: Frontend image tag
- `EKS_STORAGE_CLASS`: Storage class for EKS

## Tips

1. **Always backup before major operations**: `make db-backup`
2. **Use `make help` to see all available targets**
3. **Check status after deployment**: `make kind-status` or `make eks-status`
4. **Test connectivity**: `make kind-test` or `make eks-test`
5. **View logs for troubleshooting**: `make check-logs` or `make kind-logs`

## Troubleshooting

If a target fails:

1. Check the error message
2. Verify prerequisites (cluster exists, images built, etc.)
3. Check logs: `make check-logs` or `make kind-logs`
4. Verify status: `make kind-status` or `make eks-status`
5. Check documentation: `docs/troubleshooting/common-issues.md`

## Related Documentation

- [Quick Start Guide](./quick-start.md)
- [Deployment Guide](./deployment-guide.md)
- [Kind Cluster Deployment](../deployment/kind-access.md)
- [EKS Production Deployment](../deployment/eks.md)
- [Troubleshooting](../troubleshooting/common-issues.md)

