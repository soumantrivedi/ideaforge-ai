#!/bin/bash
# Comprehensive EKS Production Deployment Script
# Handles: DB backup, migrations, secrets, configmaps, and verification
# Usage: ./scripts/deploy-eks-production.sh [EKS_NAMESPACE] [BACKEND_IMAGE_TAG] [FRONTEND_IMAGE_TAG]

set -e

EKS_NAMESPACE=${1:-"20890-ideaforge-ai-dev-58a50"}
BACKEND_IMAGE_TAG=${2:-"latest"}
FRONTEND_IMAGE_TAG=${3:-"latest"}
EKS_REGION=${EKS_REGION:-"us-east-1"}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-"ideaforge-ai"}

echo "🚀 Starting EKS Production Deployment"
echo "======================================"
echo "Namespace: $EKS_NAMESPACE"
echo "Backend Image: ideaforge-ai-backend:$BACKEND_IMAGE_TAG"
echo "Frontend Image: ideaforge-ai-frontend:$FRONTEND_IMAGE_TAG"
echo "Region: $EKS_REGION"
echo "Cluster: $EKS_CLUSTER_NAME"
echo ""

# Verify kubectl context
echo "🔍 Verifying kubectl context..."
CURRENT_CONTEXT=$(kubectl config current-context)
if [[ ! "$CURRENT_CONTEXT" =~ "$EKS_CLUSTER_NAME" ]]; then
    echo "⚠️  Warning: Current context is $CURRENT_CONTEXT"
    echo "   Expected context to contain: $EKS_CLUSTER_NAME"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

# Verify namespace exists
echo "🔍 Verifying namespace..."
if ! kubectl get namespace "$EKS_NAMESPACE" &> /dev/null; then
    echo "❌ Namespace $EKS_NAMESPACE does not exist"
    echo "   Creating namespace..."
    kubectl create namespace "$EKS_NAMESPACE"
    echo "✅ Namespace created"
else
    echo "✅ Namespace exists"
fi

# Step 1: Database Backup (if database exists)
echo ""
echo "📦 Step 1: Database Backup"
echo "-------------------------"
POSTGRES_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$POSTGRES_POD" ]; then
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backups/eks_db_backup_${EKS_NAMESPACE}_${BACKUP_TIMESTAMP}.sql"
    mkdir -p backups
    
    echo "💾 Creating database backup..."
    kubectl exec -n "$EKS_NAMESPACE" "$POSTGRES_POD" -- pg_dump -U agentic_pm -d agentic_pm_db \
        --clean --if-exists --create \
        --format=plain \
        --no-owner --no-privileges \
        > "$BACKUP_FILE" 2>&1 || {
        echo "⚠️  Warning: Database backup failed, but continuing..."
    }
    
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "✅ Database backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        echo "⚠️  Warning: Backup file is empty or missing"
    fi
else
    echo "ℹ️  No existing PostgreSQL pod found, skipping backup (fresh install)"
fi

# Step 2: Load Secrets and ConfigMaps
echo ""
echo "📋 Step 2: Loading Secrets and ConfigMaps"
echo "-----------------------------------------"
if [ -f ".env" ]; then
    echo "📦 Loading secrets from .env file..."
    make eks-load-secrets EKS_NAMESPACE="$EKS_NAMESPACE" || {
        echo "⚠️  Warning: Failed to load secrets from .env"
        echo "   Make sure .env file exists and contains API keys"
    }
else
    echo "⚠️  Warning: .env file not found"
    echo "   Secrets must be manually configured in Kubernetes"
    echo "   Use: kubectl create secret generic ideaforge-ai-secrets --from-literal=OPENAI_API_KEY=... -n $EKS_NAMESPACE"
fi

# Apply ConfigMaps
echo "📋 Applying ConfigMaps..."
kubectl apply -f k8s/eks/configmap.yaml -n "$EKS_NAMESPACE" || {
    echo "⚠️  Warning: Failed to apply configmap"
}

# Step 3: Database Setup and Migrations
echo ""
echo "🗄️  Step 3: Database Setup and Migrations"
echo "-----------------------------------------"

# Create ConfigMaps for migrations and seed data
echo "📦 Creating database ConfigMaps..."
./k8s/create-db-configmaps.sh "$EKS_NAMESPACE" || {
    echo "⚠️  Warning: Failed to create database ConfigMaps"
}

# Run database setup job (includes migrations)
echo "🔄 Running database setup job..."
kubectl delete job db-setup -n "$EKS_NAMESPACE" --ignore-not-found=true
kubectl apply -f k8s/eks/db-setup-job.yaml -n "$EKS_NAMESPACE"

echo "⏳ Waiting for database setup to complete..."
if kubectl wait --for=condition=complete --timeout=300s job/db-setup -n "$EKS_NAMESPACE" 2>/dev/null; then
    echo "✅ Database setup completed"
else
    echo "❌ Database setup job failed or timed out"
    echo "📋 Job logs:"
    kubectl logs -n "$EKS_NAMESPACE" job/db-setup --tail=50
    exit 1
fi

# Step 4: Deploy Application
echo ""
echo "🚀 Step 4: Deploying Application"
echo "--------------------------------"

# Update image tags in deployment files
echo "🔄 Updating image tags..."
sed -i.bak "s|image:.*ideaforge-ai-backend.*|image: ideaforge-ai-backend:$BACKEND_IMAGE_TAG|g" k8s/eks/backend.yaml
sed -i.bak "s|image:.*ideaforge-ai-frontend.*|image: ideaforge-ai-frontend:$FRONTEND_IMAGE_TAG|g" k8s/eks/frontend.yaml

# Apply deployments
echo "📦 Applying backend deployment..."
kubectl apply -f k8s/eks/backend.yaml -n "$EKS_NAMESPACE"

echo "📦 Applying frontend deployment..."
kubectl apply -f k8s/eks/frontend.yaml -n "$EKS_NAMESPACE"

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl rollout status deployment/backend -n "$EKS_NAMESPACE" --timeout=300s
kubectl rollout status deployment/frontend -n "$EKS_NAMESPACE" --timeout=300s

# Step 5: Verification
echo ""
echo "✅ Step 5: Verification"
echo "---------------------"

# Check pods
echo "🔍 Checking pod status..."
kubectl get pods -n "$EKS_NAMESPACE" -l app=backend
kubectl get pods -n "$EKS_NAMESPACE" -l app=frontend

# Check API keys are loaded
echo ""
echo "🔍 Verifying API keys in secrets..."
OPENAI_KEY=$(kubectl get secret ideaforge-ai-secrets -n "$EKS_NAMESPACE" -o jsonpath='{.data.OPENAI_API_KEY}' 2>/dev/null | base64 -d || echo "")
ANTHROPIC_KEY=$(kubectl get secret ideaforge-ai-secrets -n "$EKS_NAMESPACE" -o jsonpath='{.data.ANTHROPIC_API_KEY}' 2>/dev/null | base64 -d || echo "")
GOOGLE_KEY=$(kubectl get secret ideaforge-ai-secrets -n "$EKS_NAMESPACE" -o jsonpath='{.data.GOOGLE_API_KEY}' 2>/dev/null | base64 -d || echo "")

if [ -n "$OPENAI_KEY" ] && [ "$OPENAI_KEY" != "" ]; then
    echo "✅ OpenAI API key is configured"
else
    echo "⚠️  OpenAI API key is not configured"
fi

if [ -n "$ANTHROPIC_KEY" ] && [ "$ANTHROPIC_KEY" != "" ]; then
    echo "✅ Anthropic API key is configured"
else
    echo "⚠️  Anthropic API key is not configured"
fi

if [ -n "$GOOGLE_KEY" ] && [ "$GOOGLE_KEY" != "" ]; then
    echo "✅ Google API key is configured"
else
    echo "⚠️  Google API key is not configured"
fi

# Check backend logs for Agno initialization
echo ""
echo "🔍 Checking backend logs for Agno initialization..."
BACKEND_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$BACKEND_POD" ]; then
    echo "📋 Recent backend logs:"
    kubectl logs -n "$EKS_NAMESPACE" "$BACKEND_POD" --tail=30 | grep -i "agno\|provider\|orchestrator" || echo "   (No Agno-related logs found)"
    
    # Check health endpoint
    echo ""
    echo "🔍 Checking backend health..."
    BACKEND_SVC=$(kubectl get svc -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$BACKEND_SVC" ]; then
        kubectl run -it --rm curl-test --image=curlimages/curl:latest --restart=Never -n "$EKS_NAMESPACE" -- \
            curl -s http://$BACKEND_SVC:8000/health || echo "   (Health check failed)"
    fi
fi

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📋 Summary:"
echo "   - Namespace: $EKS_NAMESPACE"
echo "   - Backend: ideaforge-ai-backend:$BACKEND_IMAGE_TAG"
echo "   - Frontend: ideaforge-ai-frontend:$FRONTEND_IMAGE_TAG"
echo "   - Database: Setup and migrations completed"
if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    echo "   - Backup: $BACKUP_FILE"
fi
echo ""
echo "💡 Next steps:"
echo "   1. Verify API keys are configured in secrets"
echo "   2. Check backend logs for Agno initialization"
echo "   3. Test the application endpoints"
echo "   4. Monitor pod health: kubectl get pods -n $EKS_NAMESPACE"
