# EKS Deployment Guide

## Overview

This guide explains how to deploy IdeaForge AI to an Amazon EKS (Elastic Kubernetes Service) cluster with configurable namespaces.

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **kubectl** installed and configured
3. **EKS Cluster** created and accessible
4. **AWS Load Balancer Controller** installed in the cluster
5. **Docker images** published to a container registry (GHCR, ECR, etc.)

## Configuration

### Environment Variables

You can configure the EKS deployment using environment variables or make target parameters:

```bash
# Required
export EKS_CLUSTER_NAME=ideaforge-ai          # Your EKS cluster name
export EKS_REGION=us-east-1                   # AWS region
export EKS_NAMESPACE=ideaforge-production     # Target namespace (default: ideaforge-ai)

# Optional
export EKS_IMAGE_REGISTRY=ghcr.io/soumantrivedi/ideaforge-ai  # Image registry
export EKS_IMAGE_TAG=latest                   # Image tag (default: latest)
```

### Configure kubectl for EKS

```bash
aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $EKS_REGION
```

## Deployment Steps

### 1. Prepare Secrets

Create `k8s/secrets.yaml` with production secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ideaforge-ai-secrets
  namespace: ideaforge-ai
type: Opaque
stringData:
  POSTGRES_PASSWORD: <strong-password>
  SESSION_SECRET: <session-secret>
  API_KEY_ENCRYPTION_KEY: <encryption-key>
  OPENAI_API_KEY: <optional>
  ANTHROPIC_API_KEY: <optional>
  GOOGLE_API_KEY: <optional>
  # ... other secrets
```

### 2. Deploy to Default Namespace

```bash
make eks-deploy
```

### 3. Deploy to Custom Namespace

```bash
# Using environment variable
export EKS_NAMESPACE=ideaforge-staging
make eks-deploy

# Or inline
make eks-deploy EKS_NAMESPACE=ideaforge-staging
```

### 4. Deploy with Custom Image Tag

```bash
make eks-deploy \
  EKS_NAMESPACE=ideaforge-production \
  EKS_IMAGE_TAG=v1.0.0 \
  EKS_IMAGE_REGISTRY=ghcr.io/soumantrivedi/ideaforge-ai
```

## Make Targets

### Deploy

```bash
# Deploy to default namespace (ideaforge-ai)
make eks-deploy

# Deploy to custom namespace
make eks-deploy EKS_NAMESPACE=my-namespace

# Deploy with specific image tag
make eks-deploy EKS_NAMESPACE=prod EKS_IMAGE_TAG=v1.2.3
```

### Status

```bash
# Check deployment status
make eks-status

# Check specific namespace
make eks-status EKS_NAMESPACE=my-namespace
```

### Testing

```bash
# Test service-to-service interactions
make eks-test EKS_NAMESPACE=my-namespace
```

### Logs

```bash
# View logs
make eks-logs EKS_NAMESPACE=my-namespace
```

### Cleanup

```bash
# Clean up deployment (will prompt for confirmation)
make eks-cleanup EKS_NAMESPACE=my-namespace
```

## Architecture

### Kustomize Structure

```
k8s/
├── base/                    # Base resources
│   └── kustomization.yaml
├── overlays/
│   ├── eks/                 # EKS base overlay
│   │   ├── kustomization.yaml
│   │   ├── postgres-eks-patch.yaml
│   │   ├── redis-eks-patch.yaml
│   │   └── ingress-eks-patch.yaml
│   └── eks-<namespace>/     # Namespace-specific overlay (auto-generated)
│       ├── kustomization.yaml
│       └── namespace-patch.yaml
```

### Resource Allocation (EKS)

- **PostgreSQL**: 1-4Gi memory, 500m-2000m CPU
- **Redis**: 512Mi-1Gi memory, 200m-1000m CPU
- **Backend**: 1-2Gi memory, 500m-2000m CPU (2 replicas)
- **Frontend**: 256Mi-512Mi memory, 100m-500m CPU (2 replicas)

### Storage

- **PostgreSQL**: 20Gi gp3 EBS volume
- **Redis**: 5Gi gp3 EBS volume

## Ingress Configuration

The EKS deployment uses AWS Application Load Balancer (ALB) for ingress.

### Update Ingress Domain

Edit `k8s/overlays/eks/ingress-eks-patch.yaml`:

```yaml
spec:
  rules:
  - host: ideaforge.yourdomain.com  # Update this
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
  - host: api.ideaforge.yourdomain.com  # Update this
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```

### SSL/TLS Certificate

Update the certificate ARN in `k8s/overlays/eks/ingress-eks-patch.yaml`:

```yaml
annotations:
  alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:region:account:certificate/cert-id"
```

## Multi-Namespace Deployment

You can deploy to multiple namespaces simultaneously:

```bash
# Production
make eks-deploy EKS_NAMESPACE=ideaforge-prod EKS_IMAGE_TAG=v1.0.0

# Staging
make eks-deploy EKS_NAMESPACE=ideaforge-staging EKS_IMAGE_TAG=latest

# Development
make eks-deploy EKS_NAMESPACE=ideaforge-dev EKS_IMAGE_TAG=dev
```

Each namespace will have:
- Isolated resources
- Separate databases (PVCs)
- Independent scaling
- Separate ingress rules (if configured)

## Troubleshooting

### Check Cluster Access

```bash
kubectl cluster-info
kubectl get nodes
```

### Check Namespace

```bash
kubectl get namespaces
kubectl get all -n $EKS_NAMESPACE
```

### Check Pod Status

```bash
kubectl get pods -n $EKS_NAMESPACE -o wide
kubectl describe pod <pod-name> -n $EKS_NAMESPACE
```

### Check Ingress

```bash
kubectl get ingress -n $EKS_NAMESPACE
kubectl describe ingress ideaforge-ai-ingress -n $EKS_NAMESPACE
```

### Check Logs

```bash
make eks-logs EKS_NAMESPACE=$EKS_NAMESPACE
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl exec -it -n $EKS_NAMESPACE deployment/postgres -- psql -U agentic_pm -d agentic_pm_db

# Check Redis
kubectl exec -it -n $EKS_NAMESPACE deployment/redis -- redis-cli ping
```

## Best Practices

1. **Use separate namespaces** for different environments (dev, staging, prod)
2. **Use specific image tags** for production (not `latest`)
3. **Configure resource limits** based on your workload
4. **Set up monitoring** and alerting for your EKS cluster
5. **Use AWS Secrets Manager** or External Secrets Operator for sensitive data
6. **Enable backup** for PostgreSQL volumes
7. **Configure autoscaling** for pods and nodes
8. **Use Network Policies** for additional security

## Example: Full Production Deployment

```bash
# Set environment variables
export EKS_CLUSTER_NAME=ideaforge-prod-cluster
export EKS_REGION=us-east-1
export EKS_NAMESPACE=ideaforge-production
export EKS_IMAGE_REGISTRY=ghcr.io/soumantrivedi/ideaforge-ai
export EKS_IMAGE_TAG=v1.0.0

# Configure kubectl
aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $EKS_REGION

# Deploy
make eks-deploy

# Verify
make eks-status

# Test
make eks-test
```

## Cleanup

To remove a deployment:

```bash
make eks-cleanup EKS_NAMESPACE=ideaforge-production
```

This will:
- Delete all resources in the namespace
- Remove the namespace
- Clean up generated kustomization files

**Warning**: This will delete all data including databases!

