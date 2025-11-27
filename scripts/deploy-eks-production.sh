#!/bin/bash
# EKS Production Deployment Script
# This script handles the complete EKS deployment with verification

set -e

EKS_NAMESPACE=${1:-"20890-ideaforge-ai-dev-58a50"}
BACKEND_TAG="28a283d"
FRONTEND_TAG="28a283d"
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-"ideaforge-ai"}
EKS_REGION=${EKS_REGION:-"us-east-1"}

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 EKS Production Deployment${NC}"
echo "=============================="
echo "Namespace: $EKS_NAMESPACE"
echo "Backend Tag: $BACKEND_TAG"
echo "Frontend Tag: $FRONTEND_TAG"
echo "Cluster: $EKS_CLUSTER_NAME"
echo "Region: $EKS_REGION"
echo ""

# Step 1: Check kubectl configuration
echo -e "${YELLOW}Step 1: Checking kubectl configuration...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ kubectl not configured${NC}"
    echo "   Configuring kubectl for EKS..."
    aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" || {
        echo -e "${RED}❌ Failed to configure kubectl. Please ensure:${NC}"
        echo "   1. AWS CLI is configured"
        echo "   2. You have access to the EKS cluster"
        echo "   3. Cluster name and region are correct"
        exit 1
    }
fi
echo -e "${GREEN}✅ kubectl configured${NC}"

# Step 2: Verify namespace exists
echo -e "${YELLOW}Step 2: Verifying namespace exists...${NC}"
if ! kubectl get namespace "$EKS_NAMESPACE" &> /dev/null; then
    echo -e "${RED}❌ Namespace $EKS_NAMESPACE does not exist${NC}"
    echo "   Please create the namespace first or verify the namespace name"
    exit 1
fi
echo -e "${GREEN}✅ Namespace exists${NC}"

# Step 3: Clean up old replicasets
echo -e "${YELLOW}Step 3: Cleaning up old replicasets...${NC}"
OLD_RS=$(kubectl get replicasets -n "$EKS_NAMESPACE" -o json 2>/dev/null | \
    jq -r '.items[] | select(.spec.replicas == 0) | .metadata.name' 2>/dev/null || echo "")

if [ -n "$OLD_RS" ]; then
    echo "$OLD_RS" | while read rs; do
        if [ -n "$rs" ]; then
            echo "   Deleting: $rs"
            kubectl delete replicaset "$rs" -n "$EKS_NAMESPACE" --ignore-not-found=true
        fi
    done
    echo -e "${GREEN}✅ Old replicasets cleaned${NC}"
else
    echo -e "${GREEN}✅ No old replicasets found${NC}"
fi

# Step 4: Setup GHCR secret
echo -e "${YELLOW}Step 4: Setting up GHCR secret...${NC}"
make eks-setup-ghcr-secret EKS_NAMESPACE="$EKS_NAMESPACE" || {
    echo -e "${YELLOW}⚠️  GHCR secret setup skipped (may already exist)${NC}"
}

# Step 5: Load secrets from .env
echo -e "${YELLOW}Step 5: Loading secrets from .env...${NC}"
if [ -f .env ]; then
    make eks-load-secrets EKS_NAMESPACE="$EKS_NAMESPACE" || {
        echo -e "${YELLOW}⚠️  Secret loading failed, continuing...${NC}"
    }
else
    echo -e "${YELLOW}⚠️  .env file not found, skipping secret loading${NC}"
fi

# Step 6: Update ConfigMaps
echo -e "${YELLOW}Step 6: Updating ConfigMaps...${NC}"
EKS_NAMESPACE="$EKS_NAMESPACE" bash k8s/create-db-configmaps.sh || {
    echo -e "${YELLOW}⚠️  ConfigMap update failed, continuing...${NC}"
}

# Step 7: Update image tags in deployments
echo -e "${YELLOW}Step 7: Updating deployment images...${NC}"
kubectl set image deployment/backend backend=ghcr.io/soumantrivedi/ideaforge-ai/backend:$BACKEND_TAG -n "$EKS_NAMESPACE" || {
    echo -e "${RED}❌ Failed to update backend image${NC}"
    exit 1
}
kubectl set image deployment/frontend frontend=ghcr.io/soumantrivedi/ideaforge-ai/frontend:$FRONTEND_TAG -n "$EKS_NAMESPACE" || {
    echo -e "${RED}❌ Failed to update frontend image${NC}"
    exit 1
}
echo -e "${GREEN}✅ Image tags updated${NC}"

# Step 8: Wait for rollout
echo -e "${YELLOW}Step 8: Waiting for deployments to roll out...${NC}"
kubectl rollout status deployment/backend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Backend rollout timeout, checking status...${NC}"
    kubectl get pods -n "$EKS_NAMESPACE" -l app=backend
}
kubectl rollout status deployment/frontend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Frontend rollout timeout, checking status...${NC}"
    kubectl get pods -n "$EKS_NAMESPACE" -l app=frontend
}

# Step 9: Verify deployment
echo -e "${YELLOW}Step 9: Verifying deployment...${NC}"
echo ""
echo -e "${BLUE}Pod Status:${NC}"
kubectl get pods -n "$EKS_NAMESPACE" -l 'app in (backend,frontend)'

echo ""
echo -e "${BLUE}Image Tags:${NC}"
BACKEND_IMAGE=$(kubectl get deployment backend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
FRONTEND_IMAGE=$(kubectl get deployment frontend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
echo "Backend: $BACKEND_IMAGE"
echo "Frontend: $FRONTEND_IMAGE"

if echo "$BACKEND_IMAGE" | grep -q "$BACKEND_TAG" && echo "$FRONTEND_IMAGE" | grep -q "$FRONTEND_TAG"; then
    echo -e "${GREEN}✅ Image tags match expected tags${NC}"
else
    echo -e "${YELLOW}⚠️  Image tags may not match expected tags${NC}"
fi

# Step 10: Verify async endpoints
echo ""
echo -e "${YELLOW}Step 10: Verifying async endpoints...${NC}"
BACKEND_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$BACKEND_POD" ]; then
    echo "   Checking backend pod: $BACKEND_POD"
    
    # Check if job service can be imported
    kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
        python -c "from backend.services.job_service import job_service; print('✅ Job service imported')" 2>/dev/null && \
        echo -e "${GREEN}✅ Job service available${NC}" || \
        echo -e "${YELLOW}⚠️  Could not verify job service (may need to check logs)${NC}"
    
    # Check backend logs
    echo "   Recent backend logs:"
    kubectl logs -n "$EKS_NAMESPACE" "$BACKEND_POD" --tail=20 | grep -i "job\|async\|submit" | head -3 || echo "      (No async endpoint logs found yet)"
else
    echo -e "${YELLOW}⚠️  Backend pod not found${NC}"
fi

# Step 11: Check Redis
echo ""
echo -e "${YELLOW}Step 11: Checking Redis...${NC}"
REDIS_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$REDIS_POD" ]; then
    kubectl exec -n "$EKS_NAMESPACE" "$REDIS_POD" -- redis-cli ping 2>/dev/null && \
        echo -e "${GREEN}✅ Redis is accessible${NC}" || \
        echo -e "${YELLOW}⚠️  Redis ping failed${NC}"
else
    echo -e "${YELLOW}⚠️  Redis pod not found${NC}"
fi

echo ""
echo -e "${GREEN}✅ EKS Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
echo "===================="
kubectl get all -n "$EKS_NAMESPACE" -l 'app in (backend,frontend,redis,postgres)' | head -20

echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Test async endpoint: ./scripts/verify-async-endpoints.sh $EKS_NAMESPACE"
echo "2. Monitor logs: kubectl logs -n $EKS_NAMESPACE -l app=backend -f"
echo "3. Check ingress: kubectl get ingress -n $EKS_NAMESPACE"

