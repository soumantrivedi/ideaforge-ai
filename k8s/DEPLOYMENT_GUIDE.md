# Kubernetes Deployment Guide

This guide covers deploying IdeaForge AI to Kubernetes clusters (Kind for testing, EKS for production).

## Quick Start

### Test Locally with Kind

```bash
# 1. Build Docker images first
make build

# 2. Deploy to kind (creates cluster, installs ingress, loads images, deploys)
make kind-deploy

# 3. Test service-to-service interactions
make kind-test

# 4. Check status
make kind-status

# 5. View logs
make kind-logs

# 6. Access the application
# Add to /etc/hosts:
#   127.0.0.1 ideaforge.local
#   127.0.0.1 api.ideaforge.local
# Then visit: http://ideaforge.local
```

### Deploy to EKS

```bash
# 1. Create namespace first (REQUIRED - deployment will NOT create it)
kubectl create namespace 20890-ideaforge-ai-dev-58a50

# 2. Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Deploy with specific image tags (recommended)
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=fab20a2 \
  FRONTEND_IMAGE_TAG=e1dc1da

# 4. Test
make eks-test EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

# 5. Check status
make eks-status EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
```

**Note**: The `eks-deploy-full` target handles:
- GHCR secret setup (for pulling images from GitHub Container Registry)
- Namespace preparation (updates manifests with namespace and image tags)
- Secrets loading (from `.env` file)
- Full deployment

**⚠️ Important**: The namespace must exist before deployment. The system will verify it exists but will NOT create it.

## Make Targets Reference

### Kind Cluster (Local Testing)

| Target | Description |
|--------|-------------|
| `make kind-create` | Create a local kind cluster |
| `make kind-delete` | Delete the kind cluster |
| `make kind-setup-ingress` | Install NGINX ingress controller |
| `make kind-load-images` | Load Docker images into kind |
| `make kind-deploy` | Full deployment (creates cluster, installs ingress, loads images, deploys) |
| `make kind-test` | Test service-to-service interactions |
| `make kind-status` | Show deployment status |
| `make kind-logs` | Show application logs |
| `make kind-cleanup` | Clean up deployment (keeps cluster) |

### EKS Cluster (Production)

| Target | Description |
|--------|-------------|
| `make eks-deploy` | Deploy to EKS cluster |
| `make eks-test` | Test service-to-service interactions |
| `make eks-status` | Show deployment status |
| `make eks-logs` | Show application logs |
| `make eks-cleanup` | Clean up deployment |

### Generic Kubernetes

| Target | Description |
|--------|-------------|
| `make k8s-deploy` | Deploy to current kubectl context |
| `make k8s-test` | Test service-to-service interactions |
| `make k8s-status` | Show deployment status |
| `make k8s-logs` | Show application logs |

## Service-to-Service Testing

The `kind-test` and `eks-test` targets verify:

1. ✅ PostgreSQL connectivity
2. ✅ Redis connectivity
3. ✅ Backend → PostgreSQL connection
4. ✅ Backend → Redis connection
5. ✅ Backend health endpoint
6. ✅ Frontend → Backend connection
7. ✅ Ingress/external access

## Configuration

### Environment Variables

Key variables you can override:

- `K8S_NAMESPACE`: Kubernetes namespace (default: `ideaforge-ai`)
- `K8S_DIR`: Directory with k8s manifests (default: `k8s`)
- `KIND_CLUSTER_NAME`: Kind cluster name (default: `ideaforge-ai`)
- `EKS_CLUSTER_NAME`: EKS cluster name (default: `ideaforge-ai`)
- `EKS_REGION`: AWS region (default: `us-east-1`)

Example:
```bash
make kind-deploy K8S_NAMESPACE=ideaforge-dev KIND_CLUSTER_NAME=ideaforge-dev
```

## Troubleshooting

### Kind Cluster Issues

```bash
# Check cluster status
kind get clusters

# Get cluster kubeconfig
kubectl cluster-info --context kind-ideaforge-ai

# Check pod status
kubectl get pods -n ideaforge-ai --context kind-ideaforge-ai

# Describe pod for errors
kubectl describe pod <pod-name> -n ideaforge-ai --context kind-ideaforge-ai
```

### EKS Cluster Issues

```bash
# Verify kubectl is configured
kubectl cluster-info

# Check node status
kubectl get nodes

# Check pod status
kubectl get pods -n ideaforge-ai

# Check events
kubectl get events -n ideaforge-ai --sort-by='.lastTimestamp'
```

### Service Connectivity Issues

```bash
# Test from backend pod
kubectl exec -it deployment/backend -n ideaforge-ai -- sh
# Then: nc -z postgres 5432
# Then: nc -z redis 6379

# Check service endpoints
kubectl get endpoints -n ideaforge-ai
```

## Ingress Configuration

### Kind (NGINX Ingress)

- Uses `ingress-kind.yaml` with NGINX annotations
- Access via `ideaforge.local` and `api.ideaforge.local`
- Add to `/etc/hosts`: `127.0.0.1 ideaforge.local api.ideaforge.local`

### EKS (AWS ALB)

- Uses `ingress.yaml` with ALB annotations
- Requires:
  - AWS Load Balancer Controller installed
  - ACM certificate ARN
  - Domain DNS configured
- Update `ingress.yaml` with your domain and certificate ARN

## Next Steps

1. **Update Secrets**: Edit `k8s/secrets.yaml` with production values
2. **Update Images**: Update image references in `backend.yaml` and `frontend.yaml`
3. **Update Ingress**: Configure domain and certificate in `ingress.yaml`
4. **Test Locally**: Use `make kind-deploy` and `make kind-test`
5. **Deploy to EKS**: Use `make eks-deploy` after testing

