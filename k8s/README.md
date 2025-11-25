# Kubernetes Manifests for IdeaForge AI

This directory contains Kubernetes manifests for deploying IdeaForge AI to an EKS cluster.

## Prerequisites

1. **EKS Cluster**: An AWS EKS cluster with:
   - AWS Load Balancer Controller installed
   - EBS CSI driver for persistent volumes
   - kubectl configured to access your cluster

2. **Container Registry**: Docker images published to a registry (e.g., GHCR, ECR)
   - Backend image: `ghcr.io/YOUR_ORG/YOUR_REPO/backend:latest`
   - Frontend image: `ghcr.io/YOUR_ORG/YOUR_REPO/frontend:latest`

3. **Secrets**: All sensitive data configured in secrets

## File Structure

```
k8s/
├── namespace.yaml          # Namespace definition
├── configmap.yaml          # Non-sensitive configuration
├── secrets.yaml            # Sensitive data (⚠️ UPDATE BEFORE DEPLOYING!)
├── postgres.yaml           # PostgreSQL database deployment
├── redis.yaml              # Redis cache deployment
├── backend.yaml            # Backend API deployment
├── frontend.yaml           # Frontend web deployment
├── ingress.yaml            # Ingress configuration for external access
├── kustomization.yaml      # Kustomize configuration
└── README.md              # This file
```

## Quick Start

### Option A: Using Make Targets (Recommended)

#### Test Locally with Kind

```bash
# Full deployment to kind cluster (creates cluster, installs ingress, deploys)
make kind-deploy

# Test service-to-service interactions
make kind-test

# Check status
make kind-status

# View logs
make kind-logs

# Clean up (keeps cluster)
make kind-cleanup

# Delete cluster
make kind-delete
```

#### Deploy to EKS

```bash
# Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# Deploy to EKS
make eks-deploy

# Test service-to-service interactions
make eks-test

# Check status
make eks-status

# View logs
make eks-logs
```

### Option B: Manual Deployment

### 1. Update Secrets

**⚠️ IMPORTANT**: Update `secrets.yaml` with your actual secrets before deploying:

```bash
# Edit secrets.yaml and update:
# - POSTGRES_PASSWORD
# - SESSION_SECRET
# - API_KEY_ENCRYPTION_KEY
# - All API keys and tokens
```

Or use kubectl to create/update secrets:

```bash
kubectl create secret generic ideaforge-ai-secrets \
  --from-literal=POSTGRES_PASSWORD='your-password' \
  --from-literal=SESSION_SECRET='your-session-secret' \
  --from-literal=API_KEY_ENCRYPTION_KEY='your-encryption-key' \
  --namespace=ideaforge-ai \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Update Image References

Update image references in `backend.yaml` and `frontend.yaml`:

```yaml
image: ghcr.io/YOUR_ORG/YOUR_REPO/backend:latest
```

### 3. Update Ingress Configuration

Update `ingress.yaml` with:
- Your domain names
- ACM certificate ARN
- S3 bucket for access logs (optional)

### 4. Update ConfigMap

Update `configmap.yaml` with your frontend API URL:

```yaml
VITE_API_URL: "https://api.ideaforge.ai"
```

### 5. Deploy Manually

#### Option A: Using kubectl (apply all files)

```bash
# Apply all manifests
kubectl apply -f k8s/

# Or apply individually
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

#### Option B: Using kustomize

```bash
kubectl apply -k k8s/
```

### 6. Verify Deployment

```bash
# Check all resources
kubectl get all -n ideaforge-ai

# Check pods
kubectl get pods -n ideaforge-ai

# Check services
kubectl get svc -n ideaforge-ai

# Check ingress
kubectl get ingress -n ideaforge-ai

# Check logs
kubectl logs -f deployment/backend -n ideaforge-ai
kubectl logs -f deployment/frontend -n ideaforge-ai
```

### 7. Get Ingress URL

```bash
# For ALB Ingress
kubectl get ingress ideaforge-ai-ingress -n ideaforge-ai

# The ADDRESS field will show your ALB DNS name
```

## Configuration Details

### Storage

- **PostgreSQL**: 20Gi persistent volume (gp3 EBS)
- **Redis**: 5Gi persistent volume (gp3 EBS)

### Resources

- **Backend**: 
  - Requests: 1Gi memory, 500m CPU
  - Limits: 2Gi memory, 2000m CPU
- **Frontend**:
  - Requests: 256Mi memory, 100m CPU
  - Limits: 512Mi memory, 500m CPU
- **PostgreSQL**:
  - Requests: 512Mi memory, 250m CPU
  - Limits: 2Gi memory, 1000m CPU
- **Redis**:
  - Requests: 256Mi memory, 100m CPU
  - Limits: 512Mi memory, 500m CPU

### Replicas

- Backend: 2 replicas (adjust based on load)
- Frontend: 2 replicas (adjust based on load)
- PostgreSQL: 1 replica (single instance)
- Redis: 1 replica (single instance)

## Ingress Configuration

The ingress is configured for AWS ALB (Application Load Balancer) with:
- HTTPS termination
- SSL redirect
- Health checks
- Access logging (optional)

### Alternative: NGINX Ingress

If you prefer NGINX Ingress Controller, uncomment the NGINX ingress configuration in `ingress.yaml` and comment out the ALB configuration.

## Database Initialization

The PostgreSQL deployment includes an init container that waits for the database to be ready. For initial schema setup, you can:

1. Use a Kubernetes Job to run migrations
2. Mount init scripts via ConfigMap
3. Use an init container with your migration scripts

Example migration job:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: ideaforge-ai
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: postgres:15
        command:
        - /bin/sh
        - -c
        - |
          psql $DATABASE_URL -f /migrations/init.sql
        volumeMounts:
        - name: migrations
          mountPath: /migrations
      volumes:
      - name: migrations
        configMap:
          name: postgres-init-scripts
      restartPolicy: Never
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n ideaforge-ai

# Check events
kubectl get events -n ideaforge-ai --sort-by='.lastTimestamp'
```

### Database connection issues

```bash
# Check postgres logs
kubectl logs deployment/postgres -n ideaforge-ai

# Test connection from backend pod
kubectl exec -it deployment/backend -n ideaforge-ai -- sh
# Then: psql -h postgres -U agentic_pm -d agentic_pm_db
```

### Ingress not working

```bash
# Check ingress status
kubectl describe ingress ideaforge-ai-ingress -n ideaforge-ai

# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

## Scaling

To scale the application:

```bash
# Scale backend
kubectl scale deployment backend --replicas=3 -n ideaforge-ai

# Scale frontend
kubectl scale deployment frontend --replicas=3 -n ideaforge-ai
```

## Updating Images

```bash
# Update image tag
kubectl set image deployment/backend backend=ghcr.io/YOUR_ORG/YOUR_REPO/backend:v1.0.0 -n ideaforge-ai
kubectl set image deployment/frontend frontend=ghcr.io/YOUR_ORG/YOUR_REPO/frontend:v1.0.0 -n ideaforge-ai

# Or use kustomize
# Update kustomization.yaml with new image tags
kubectl apply -k k8s/
```

## Security Best Practices

1. **Use External Secrets**: Consider using AWS Secrets Manager with External Secrets Operator
2. **Network Policies**: Implement network policies to restrict pod-to-pod communication
3. **Pod Security Standards**: Apply pod security standards
4. **RBAC**: Configure proper RBAC for service accounts
5. **Image Scanning**: Scan container images for vulnerabilities
6. **TLS**: Always use HTTPS for ingress

## Monitoring

Consider adding:
- Prometheus for metrics
- Grafana for dashboards
- CloudWatch Container Insights
- Application-level logging (CloudWatch Logs)

## Backup

For database backups, consider:
- AWS RDS instead of in-cluster PostgreSQL
- Scheduled backup jobs using Kubernetes CronJobs
- AWS Backup for EBS volumes

