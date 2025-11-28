# EKS Production Deployment Guide

Complete step-by-step guide for deploying IdeaForge AI to Amazon EKS (Elastic Kubernetes Service) production environment.

## Prerequisites

### Required Software

1. **AWS CLI** (v2+)
   - Install: https://aws.amazon.com/cli/
   - Configure: `aws configure`
   - Verify: `aws --version`

2. **kubectl**
   - Install: https://kubernetes.io/docs/tasks/tools/
   - Verify: `kubectl version --client`

3. **Docker** (for building images, if not using CI/CD)
   - Verify: `docker --version`

4. **Git**
   - Verify: `git --version`

5. **GNU Make**
   - Verify: `make --version`

### AWS Access

- AWS account with EKS cluster access
- IAM permissions for:
  - EKS cluster access
  - EC2 (for worker nodes)
  - ECR/GHCR (for container images)
  - Secrets Manager (optional, for secrets)

### GitHub Access

- GitHub account with repository access
- GitHub Personal Access Token (PAT) with `read:packages` scope
  - Create at: https://github.com/settings/tokens
  - Required for pulling images from GitHub Container Registry (GHCR)

## Step 1: Prepare Environment

### Clone Repository

```bash
git clone <repository-url> ideaforge-ai
cd ideaforge-ai
```

### Configure Environment Variables

```bash
# Copy EKS environment template
cp env.eks.example env.eks

# Edit env.eks with production values
nano env.eks
```

**Required variables:**
```bash
# API Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
V0_API_KEY=...  # Optional, for design prototypes

# GitHub Token (for GHCR access)
GITHUB_TOKEN=ghp_...

# Atlassian (optional, for integrations)
ATLASSIAN_EMAIL=...
ATLASSIAN_API_TOKEN=...

# Database (will be set via ConfigMap/Secrets)
POSTGRES_PASSWORD=<strong-password>
SESSION_SECRET=<random-secret>
API_KEY_ENCRYPTION_KEY=<random-key>
```

### Configure kubectl for EKS

```bash
# Set your EKS cluster name and region
export EKS_CLUSTER_NAME=ideaforge-ai
export EKS_REGION=us-east-1

# Update kubeconfig
aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $EKS_REGION

# Verify connection
kubectl cluster-info
kubectl get nodes
```

## Step 2: Build and Push Images

### Option A: Using GitHub Actions (Recommended)

Images are automatically built and pushed to GHCR when you push to `main` branch.

1. **Push code to main branch**
   ```bash
   git add .
   git commit -m "feat: Production deployment"
   git push origin main
   ```

2. **Wait for GitHub Actions to complete**
   - Check: https://github.com/soumantrivedi/ideaforge-ai/actions
   - Wait for "Build and Publish Docker Images" workflow

3. **Get image tags**
   ```bash
   # Get latest commit SHA
   export BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD)
   export FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)
   
   echo "Backend: ghcr.io/soumantrivedi/ideaforge-ai/backend:$BACKEND_IMAGE_TAG"
   echo "Frontend: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$FRONTEND_IMAGE_TAG"
   ```

### Option B: Manual Build and Push

```bash
# Get current git SHA
export GIT_SHA=$(git rev-parse --short HEAD)

# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build backend
docker build -f Dockerfile.backend -t ghcr.io/soumantrivedi/ideaforge-ai/backend:$GIT_SHA .

# Build frontend
docker build -f Dockerfile.frontend -t ghcr.io/soumantrivedi/ideaforge-ai/frontend:$GIT_SHA .

# Push images
docker push ghcr.io/soumantrivedi/ideaforge-ai/backend:$GIT_SHA
docker push ghcr.io/soumantrivedi/ideaforge-ai/frontend:$GIT_SHA

# Set tags for deployment
export BACKEND_IMAGE_TAG=$GIT_SHA
export FRONTEND_IMAGE_TAG=$GIT_SHA
```

## Step 3: Setup GitHub Container Registry Secret

Kubernetes needs credentials to pull images from GHCR.

```bash
# Set your EKS namespace
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

# Setup GHCR secret
make eks-setup-ghcr-secret EKS_NAMESPACE=$EKS_NAMESPACE
```

This command:
- Reads `GITHUB_TOKEN` from `.env` or `EKS_GITHUB_TOKEN` environment variable
- Creates a `docker-registry` secret named `ghcr-secret` in your namespace
- Allows Kubernetes to pull images from `ghcr.io/soumantrivedi/ideaforge-ai`

## Step 4: Load Secrets to Kubernetes

```bash
# Load all secrets from env.eks file
make eks-load-secrets EKS_NAMESPACE=$EKS_NAMESPACE
```

This creates/updates the `ideaforge-ai-secrets` secret with:
- API keys (OpenAI, Anthropic, Google, V0)
- Database password
- Session secrets
- Integration tokens

## Step 5: Deploy Application

### Full Automated Deployment

```bash
# Single command for complete deployment
make eks-deploy-full \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$BACKEND_IMAGE_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_IMAGE_TAG
```

This command:
1. Sets up GHCR secret
2. Prepares namespace-specific manifests
3. Loads secrets
4. Deploys all components
5. Runs database migrations
6. Seeds database
7. Initializes Agno framework

### Step-by-Step Deployment

```bash
# 1. Prepare namespace-specific manifests
make eks-prepare-namespace \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$BACKEND_IMAGE_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_IMAGE_TAG

# 2. Deploy application
make eks-deploy \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$BACKEND_IMAGE_TAG \
  FRONTEND_IMAGE_TAG=$FRONTEND_IMAGE_TAG
```

## Step 6: Verify Deployment

### Check Deployment Status

```bash
# Show all resources
make eks-status EKS_NAMESPACE=$EKS_NAMESPACE

# Check pod status
kubectl get pods -n $EKS_NAMESPACE

# Check services
kubectl get svc -n $EKS_NAMESPACE

# Check ingress
kubectl get ingress -n $EKS_NAMESPACE
```

### Test Service Connectivity

```bash
# Test service-to-service communication
make eks-test EKS_NAMESPACE=$EKS_NAMESPACE
```

### Check Application Logs

```bash
# Backend logs
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=100

# Frontend logs
kubectl logs -n $EKS_NAMESPACE -l app=frontend --tail=100

# Database setup job logs
kubectl logs -n $EKS_NAMESPACE job/db-setup --tail=100
```

### Verify Health Endpoints

```bash
# Port forward for local testing
make eks-port-forward EKS_NAMESPACE=$EKS_NAMESPACE

# In another terminal, test health
curl http://localhost:8000/health
curl http://localhost:8000/api/health
```

## Step 7: Configure Ingress

### Option A: ALB Ingress (AWS Load Balancer)

```bash
# Apply ALB ingress
kubectl apply -f k8s/eks/ingress-alb.yaml

# Get ingress URL
kubectl get ingress -n $EKS_NAMESPACE -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}'
```

### Option B: NGINX Ingress

```bash
# Install NGINX ingress controller (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/aws/deploy.yaml

# Apply ingress
kubectl apply -f k8s/eks/ingress-nginx.yaml

# Get ingress URL
kubectl get ingress -n $EKS_NAMESPACE
```

## Step 8: Database Management

### Backup Database

```bash
# Use backup script
./scripts/backup-database.sh $EKS_NAMESPACE backup-$(date +%Y%m%d-%H%M%S).sql
```

### Restore Database

```bash
# Use restore script
./scripts/restore-database.sh $EKS_NAMESPACE backups/backup_file.sql
```

### Run Migrations Manually

```bash
# Run migrations script
./scripts/run-migrations.sh
```

### Add Demo Accounts

```bash
# Add demo accounts to database
make eks-add-demo-accounts EKS_NAMESPACE=$EKS_NAMESPACE
```

## Step 9: Post-Deployment Configuration

### Initialize Agno Framework

```bash
# Initialize Agno (if not done during deployment)
make eks-agno-init EKS_NAMESPACE=$EKS_NAMESPACE
```

### Update Database ConfigMaps

```bash
# Update ConfigMaps with latest migration files
make eks-update-db-configmaps EKS_NAMESPACE=$EKS_NAMESPACE
```

### Configure API Keys in UI

1. Access application via ingress URL
2. Navigate to **Settings**
3. Enter and verify API keys
4. Save configuration

## Step 10: Monitoring and Maintenance

### Monitor Pods

```bash
# Watch pod status
kubectl get pods -n $EKS_NAMESPACE -w

# Check pod resource usage
kubectl top pods -n $EKS_NAMESPACE
```

### Monitor Logs

```bash
# Follow backend logs
kubectl logs -n $EKS_NAMESPACE -l app=backend -f

# Follow frontend logs
kubectl logs -n $EKS_NAMESPACE -l app=frontend -f
```

### Scale Deployment

```bash
# Scale backend
kubectl scale deployment backend -n $EKS_NAMESPACE --replicas=3

# Scale frontend
kubectl scale deployment frontend -n $EKS_NAMESPACE --replicas=2
```

### Update Deployment

```bash
# Get new image tags
export NEW_BACKEND_TAG=$(git rev-parse --short HEAD)
export NEW_FRONTEND_TAG=$(git rev-parse --short HEAD)

# Update image tags in manifests
make eks-prepare-namespace \
  EKS_NAMESPACE=$EKS_NAMESPACE \
  BACKEND_IMAGE_TAG=$NEW_BACKEND_TAG \
  FRONTEND_IMAGE_TAG=$NEW_FRONTEND_TAG

# Apply updated manifests
kubectl apply -f k8s/eks/backend.yaml
kubectl apply -f k8s/eks/frontend.yaml

# Wait for rollout
kubectl rollout status deployment/backend -n $EKS_NAMESPACE
kubectl rollout status deployment/frontend -n $EKS_NAMESPACE
```

## Troubleshooting

### Images Not Pulling

```bash
# Check GHCR secret
kubectl get secret ghcr-secret -n $EKS_NAMESPACE

# Verify secret credentials
kubectl get secret ghcr-secret -n $EKS_NAMESPACE -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d

# Recreate secret if needed
make eks-setup-ghcr-secret EKS_NAMESPACE=$EKS_NAMESPACE
```

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod -n $EKS_NAMESPACE <pod-name>

# Check pod logs
kubectl logs -n $EKS_NAMESPACE <pod-name>

# Check init container logs
kubectl logs -n $EKS_NAMESPACE <pod-name> -c run-migrations
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -n $EKS_NAMESPACE -l app=postgres

# Check PostgreSQL logs
kubectl logs -n $EKS_NAMESPACE -l app=postgres

# Test database connection from backend pod
kubectl exec -n $EKS_NAMESPACE -it deployment/backend -- \
  python -c "from backend.database import check_db_health; print(check_db_health())"
```

### Secrets Not Loading

```bash
# Check secrets
kubectl get secrets -n $EKS_NAMESPACE

# Verify secret contents (masked)
kubectl get secret ideaforge-ai-secrets -n $EKS_NAMESPACE -o yaml

# Reload secrets
make eks-load-secrets EKS_NAMESPACE=$EKS_NAMESPACE
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n $EKS_NAMESPACE

# Check ingress events
kubectl describe ingress -n $EKS_NAMESPACE

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

## Best Practices

1. **Always backup database before major updates**
   ```bash
   ./scripts/backup-database.sh $EKS_NAMESPACE
   ```

2. **Use specific image tags, not `latest`**
   - Tag images with git SHA
   - Track which version is deployed

3. **Monitor resource usage**
   - Set up CloudWatch alarms
   - Monitor pod CPU/memory usage
   - Set up log aggregation

4. **Regular updates**
   - Keep images updated with latest code
   - Run database migrations regularly
   - Update dependencies

5. **Security**
   - Rotate secrets regularly
   - Use AWS Secrets Manager for sensitive data
   - Enable pod security policies
   - Use network policies

## Additional Resources

- [Make Targets Reference](./make-targets.md)
- [Database Migration Guide](./database-migration.md)
- [Troubleshooting Guide](../troubleshooting/common-issues.md)
- [EKS Ingress Setup](../deployment/eks-ingress.md)
- [Backup and Restore](../deployment/backups.md)

