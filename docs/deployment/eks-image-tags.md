# EKS Image Tag Configuration

## Overview

The EKS deployment supports configurable image tags for backend and frontend services. This allows you to deploy specific, stable image versions instead of always using `latest`.

## Usage

### Basic Deployment

Deploy with default tags (uses `latest` for both services):

```bash
make eks-deploy-full EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
```

### Deployment with Specific Image Tags

Deploy with specific image tags for backend and frontend:

```bash
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=fab20a2 \
  FRONTEND_IMAGE_TAG=e1dc1da
```

### Using Environment Variables

You can also set image tags as environment variables:

```bash
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
export BACKEND_IMAGE_TAG=fab20a2
export FRONTEND_IMAGE_TAG=e1dc1da

make eks-deploy-full
```

## Image Tag Format

Image tags should be:
- Git commit SHA (short): `fab20a2`, `e1dc1da`
- Semantic version: `v1.0.0`, `v1.2.3`
- Branch name: `main`, `develop`
- `latest` (default, not recommended for production)

## Finding Available Image Tags

Image tags are published to GitHub Container Registry (GHCR) with each build. You can find available tags:

1. **GitHub UI**: Navigate to `https://github.com/soumantrivedi/ideaforge-ai/pkgs/container/ideaforge-ai`
2. **GitHub CLI**: `gh api user/packages/container/ideaforge-ai/versions`
3. **Docker CLI**: `docker pull ghcr.io/soumantrivedi/ideaforge-ai/backend:tag`

## Makefile Variables

- `EKS_NAMESPACE`: Kubernetes namespace (required)
- `BACKEND_IMAGE_TAG`: Backend image tag (defaults to `latest`)
- `FRONTEND_IMAGE_TAG`: Frontend image tag (defaults to `latest`)
- `EKS_STORAGE_CLASS`: Storage class for PVCs (defaults to `default-storage-class`)

## Examples

### Deploy Latest Builds

```bash
# Get latest commit SHA
BACKEND_TAG=$(git rev-parse --short HEAD)
FRONTEND_TAG=$(git rev-parse --short HEAD)

make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=$BACKEND_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_TAG
```

### Deploy Specific Stable Versions

```bash
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=v1.0.0 \
  FRONTEND_IMAGE_TAG=v1.0.0
```

### Update Only Backend

```bash
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=new-backend-tag \
  FRONTEND_IMAGE_TAG=existing-frontend-tag
```

## Notes

- Image tags are updated in the EKS manifests before deployment
- The `eks-prepare-namespace` target handles the image tag updates
- If image tags are not specified, the system defaults to `latest`
- Always verify image tags exist in GHCR before deploying
- For production, use specific commit SHAs or semantic versions, not `latest`

