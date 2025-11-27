#!/bin/bash
# EKS Deployment Script for Async Job Processing
# Usage: ./scripts/deploy-to-eks.sh [EKS_NAMESPACE] [BACKEND_TAG] [FRONTEND_TAG]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get parameters
EKS_NAMESPACE=${1:-"20890-ideaforge-ai-dev-58a50"}
BACKEND_TAG=${2:-$(git rev-parse --short HEAD)}
FRONTEND_TAG=${3:-$(git rev-parse --short HEAD)}

echo -e "${GREEN}🚀 EKS Deployment Script${NC}"
echo "================================"
echo "Namespace: $EKS_NAMESPACE"
echo "Backend Tag: $BACKEND_TAG"
echo "Frontend Tag: $FRONTEND_TAG"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check kubectl connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ kubectl not configured or cluster not accessible${NC}"
    echo "   Configure kubectl: aws eks update-kubeconfig --name ideaforge-ai --region us-east-1"
    exit 1
fi
echo -e "${GREEN}✅ kubectl is configured${NC}"

# Check namespace exists
if ! kubectl get namespace "$EKS_NAMESPACE" &> /dev/null; then
    echo -e "${RED}❌ Namespace $EKS_NAMESPACE does not exist${NC}"
    echo "   Please create the namespace first or check the namespace name"
    exit 1
fi
echo -e "${GREEN}✅ Namespace $EKS_NAMESPACE exists${NC}"

# Update image tags in manifests
echo -e "${YELLOW}🔄 Updating image tags in manifests...${NC}"
sed -i.bak "s|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:$BACKEND_TAG|g" k8s/eks/backend.yaml
sed -i.bak "s|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$FRONTEND_TAG|g" k8s/eks/frontend.yaml
echo -e "${GREEN}✅ Image tags updated${NC}"

# Setup GHCR secret
echo -e "${YELLOW}🔐 Setting up GHCR secret...${NC}"
make eks-setup-ghcr-secret EKS_NAMESPACE="$EKS_NAMESPACE" || {
    echo -e "${YELLOW}⚠️  GHCR secret setup failed or already exists, continuing...${NC}"
}

# Load secrets from .env
echo -e "${YELLOW}📦 Loading secrets from .env...${NC}"
if [ -f .env ]; then
    make eks-load-secrets EKS_NAMESPACE="$EKS_NAMESPACE" || {
        echo -e "${YELLOW}⚠️  Secret loading failed, continuing...${NC}"
    }
else
    echo -e "${YELLOW}⚠️  .env file not found, skipping secret loading${NC}"
fi

# Create/update ConfigMaps
echo -e "${YELLOW}📦 Creating/updating ConfigMaps...${NC}"
EKS_NAMESPACE="$EKS_NAMESPACE" bash k8s/create-db-configmaps.sh || {
    echo -e "${YELLOW}⚠️  ConfigMap creation failed, continuing...${NC}"
}

# Deploy manifests
echo -e "${YELLOW}📦 Deploying Kubernetes manifests...${NC}"
find k8s/eks -name "*.yaml" ! -name "namespace.yaml" -type f -exec kubectl apply -f {} \;

# Wait for database services
echo -e "${YELLOW}⏳ Waiting for database services to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  PostgreSQL not ready, continuing...${NC}"
}
kubectl wait --for=condition=ready pod -l app=redis -n "$EKS_NAMESPACE" --timeout=120s || {
    echo -e "${YELLOW}⚠️  Redis not ready, continuing...${NC}"
}

# Wait for application pods
echo -e "${YELLOW}⏳ Waiting for application pods to be ready...${NC}"
sleep 10
kubectl wait --for=condition=ready pod -l app=backend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Backend pods not ready, continuing...${NC}"
}
kubectl wait --for=condition=ready pod -l app=frontend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Frontend pods not ready, continuing...${NC}"
}

# Show status
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${GREEN}📊 Deployment Status:${NC}"
kubectl get pods -n "$EKS_NAMESPACE" -l 'app in (backend,frontend)'
echo ""
echo -e "${GREEN}🔗 Ingress URL:${NC}"
kubectl get ingress -n "$EKS_NAMESPACE" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || \
kubectl get ingress -n "$EKS_NAMESPACE" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
echo "   (Ingress address pending...)"

echo ""
echo -e "${GREEN}✅ Deployment script completed!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Verify pods are running: kubectl get pods -n $EKS_NAMESPACE"
echo "2. Check backend logs: kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=50"
echo "3. Test async endpoint: curl -X POST https://your-domain/api/multi-agent/submit ..."
echo "4. Monitor Redis: kubectl exec -n $EKS_NAMESPACE -it deployment/redis -- redis-cli INFO memory"

