#!/bin/bash
# EKS Production Deployment with Verification
# Usage: ./scripts/deploy-eks-and-verify.sh [EKS_NAMESPACE]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

EKS_NAMESPACE=${1:-"20890-ideaforge-ai-dev-58a50"}
BACKEND_TAG="28a283d"
FRONTEND_TAG="28a283d"

echo -e "${BLUE}🚀 EKS Production Deployment with Verification${NC}"
echo "=================================================="
echo "Namespace: $EKS_NAMESPACE"
echo "Backend Tag: $BACKEND_TAG"
echo "Frontend Tag: $FRONTEND_TAG"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ kubectl not configured${NC}"
    exit 1
fi
echo -e "${GREEN}✅ kubectl configured${NC}"

# Step 1: Clean up old replicasets
echo -e "${YELLOW}🧹 Step 1: Cleaning up old replicasets...${NC}"
OLD_RS=$(kubectl get replicasets -n "$EKS_NAMESPACE" -o json 2>/dev/null | \
    jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' 2>/dev/null || echo "")

if [ -n "$OLD_RS" ]; then
    echo "$OLD_RS" | while read rs; do
        if [ -n "$rs" ]; then
            echo "   Deleting replicaset: $rs"
            kubectl delete replicaset "$rs" -n "$EKS_NAMESPACE" --ignore-not-found=true
        fi
    done
    echo -e "${GREEN}✅ Old replicasets cleaned up${NC}"
else
    echo -e "${GREEN}✅ No old replicasets found${NC}"
fi

# Step 2: Update image tags in manifests
echo -e "${YELLOW}🔄 Step 2: Updating image tags...${NC}"
sed -i.bak "s|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/backend:$BACKEND_TAG|g" k8s/eks/backend.yaml
sed -i.bak "s|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:.*|image: ghcr.io/soumantrivedi/ideaforge-ai/frontend:$FRONTEND_TAG|g" k8s/eks/frontend.yaml
echo -e "${GREEN}✅ Image tags updated${NC}"

# Step 3: Setup GHCR secret
echo -e "${YELLOW}🔐 Step 3: Setting up GHCR secret...${NC}"
make eks-setup-ghcr-secret EKS_NAMESPACE="$EKS_NAMESPACE" || {
    echo -e "${YELLOW}⚠️  GHCR secret already exists or setup failed${NC}"
}

# Step 4: Load secrets from .env
echo -e "${YELLOW}📦 Step 4: Loading secrets from .env...${NC}"
if [ -f .env ]; then
    make eks-load-secrets EKS_NAMESPACE="$EKS_NAMESPACE" || {
        echo -e "${YELLOW}⚠️  Secret loading failed, continuing...${NC}"
    }
else
    echo -e "${YELLOW}⚠️  .env file not found, skipping secret loading${NC}"
fi

# Step 5: Update ConfigMaps
echo -e "${YELLOW}📦 Step 5: Updating ConfigMaps...${NC}"
EKS_NAMESPACE="$EKS_NAMESPACE" bash k8s/create-db-configmaps.sh || {
    echo -e "${YELLOW}⚠️  ConfigMap update failed, continuing...${NC}"
}

# Step 6: Deploy manifests
echo -e "${YELLOW}📦 Step 6: Deploying Kubernetes manifests...${NC}"
find k8s/eks -name "*.yaml" ! -name "namespace.yaml" -type f -exec kubectl apply -f {} \;

# Step 7: Wait for pods
echo -e "${YELLOW}⏳ Step 7: Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n "$EKS_NAMESPACE" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=redis -n "$EKS_NAMESPACE" --timeout=120s || true
sleep 10
kubectl wait --for=condition=ready pod -l app=backend -n "$EKS_NAMESPACE" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=frontend -n "$EKS_NAMESPACE" --timeout=300s || true

# Step 8: Verify deployment
echo -e "${YELLOW}🔍 Step 8: Verifying deployment...${NC}"
echo ""
echo -e "${BLUE}Pod Status:${NC}"
kubectl get pods -n "$EKS_NAMESPACE" -l 'app in (backend,frontend)'

echo ""
echo -e "${BLUE}Image Tags:${NC}"
kubectl get deployment backend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' && echo ""
kubectl get deployment frontend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' && echo ""

echo ""
echo -e "${BLUE}Backend Logs (checking for async endpoints):${NC}"
kubectl logs -n "$EKS_NAMESPACE" -l app=backend --tail=50 | grep -i "job\|async\|submit" || echo "   (No async endpoint logs found yet)"

echo ""
echo -e "${BLUE}Redis Status:${NC}"
kubectl exec -n "$EKS_NAMESPACE" -it deployment/redis -- redis-cli ping 2>/dev/null || echo "   (Redis not accessible)"

echo ""
echo -e "${GREEN}✅ EKS Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}📝 Next: Test async endpoints${NC}"
echo "1. Submit job: POST /api/multi-agent/submit"
echo "2. Check status: GET /api/multi-agent/jobs/{job_id}/status"
echo "3. Get result: GET /api/multi-agent/jobs/{job_id}/result"

