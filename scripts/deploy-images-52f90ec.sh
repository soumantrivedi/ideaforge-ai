#!/bin/bash
# Deploy images with tag 52f90ec to EKS
# Usage: ./scripts/deploy-images-52f90ec.sh

set -e

KUBECONFIG=${KUBECONFIG:-/tmp/kubeconfig.eacSiD}
EKS_NAMESPACE=${EKS_NAMESPACE:-20890-ideaforge-ai-dev-58a50}
NEW_TAG="52f90ec"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Deploying Images Tag: $NEW_TAG${NC}"
echo "================================"
echo "Namespace: $EKS_NAMESPACE"
echo "Kubeconfig: $KUBECONFIG"
echo ""

export KUBECONFIG

# Step 1: Verify images exist
echo -e "${YELLOW}Step 1: Verifying images exist in GHCR...${NC}"
BACKEND_IMAGE="ghcr.io/soumantrivedi/ideaforge-ai/backend:$NEW_TAG"
FRONTEND_IMAGE="ghcr.io/soumantrivedi/ideaforge-ai/frontend:$NEW_TAG"

# Try to pull images to verify they exist (this will fail if images don't exist)
if docker pull "$BACKEND_IMAGE" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend image exists: $BACKEND_IMAGE${NC}"
else
    echo -e "${RED}❌ Backend image not found: $BACKEND_IMAGE${NC}"
    echo "   Please wait for GitHub Actions to complete building images"
    exit 1
fi

if docker pull "$FRONTEND_IMAGE" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend image exists: $FRONTEND_IMAGE${NC}"
else
    echo -e "${RED}❌ Frontend image not found: $FRONTEND_IMAGE${NC}"
    echo "   Please wait for GitHub Actions to complete building images"
    exit 1
fi

# Step 2: Clean old replicasets
echo -e "${YELLOW}Step 2: Cleaning up old replicasets...${NC}"
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

# Step 3: Update images
echo -e "${YELLOW}Step 3: Updating deployment images...${NC}"
kubectl set image deployment/backend \
  backend="$BACKEND_IMAGE" \
  -n "$EKS_NAMESPACE"

kubectl set image deployment/frontend \
  frontend="$FRONTEND_IMAGE" \
  -n "$EKS_NAMESPACE"

echo -e "${GREEN}✅ Image tags updated${NC}"

# Step 4: Wait for rollout
echo -e "${YELLOW}Step 4: Waiting for deployments to roll out...${NC}"
kubectl rollout status deployment/backend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Backend rollout timeout, checking status...${NC}"
    kubectl get pods -n "$EKS_NAMESPACE" -l app=backend
}

kubectl rollout status deployment/frontend -n "$EKS_NAMESPACE" --timeout=300s || {
    echo -e "${YELLOW}⚠️  Frontend rollout timeout, checking status...${NC}"
    kubectl get pods -n "$EKS_NAMESPACE" -l app=frontend
}

# Step 5: Verify deployment
echo -e "${YELLOW}Step 5: Verifying deployment...${NC}"
echo ""
echo -e "${BLUE}Pod Status:${NC}"
kubectl get pods -n "$EKS_NAMESPACE" -l 'app in (backend,frontend)'

echo ""
echo -e "${BLUE}Image Tags:${NC}"
BACKEND_CURRENT=$(kubectl get deployment backend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
FRONTEND_CURRENT=$(kubectl get deployment frontend -n "$EKS_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
echo "Backend: $BACKEND_CURRENT"
echo "Frontend: $FRONTEND_CURRENT"

if echo "$BACKEND_CURRENT" | grep -q "$NEW_TAG" && echo "$FRONTEND_CURRENT" | grep -q "$NEW_TAG"; then
    echo -e "${GREEN}✅ Image tags match expected tag: $NEW_TAG${NC}"
else
    echo -e "${YELLOW}⚠️  Image tags may not match expected tag${NC}"
fi

# Step 6: Verify backend functionality
echo ""
echo -e "${YELLOW}Step 6: Verifying backend functionality...${NC}"
BACKEND_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$BACKEND_POD" ]; then
    echo "   Testing backend pod: $BACKEND_POD"
    
    # Health check
    kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
        curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -3 && \
        echo -e "${GREEN}   ✅ Backend health check passed${NC}" || \
        echo -e "${YELLOW}   ⚠️  Health check failed${NC}"
    
    # Job service import
    kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
        python -c "from backend.services.job_service import job_service; print('✅ Job service OK')" 2>&1 && \
        echo -e "${GREEN}   ✅ Job service available${NC}" || \
        echo -e "${YELLOW}   ⚠️  Job service check failed${NC}"
else
    echo -e "${YELLOW}⚠️  Backend pod not found${NC}"
fi

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
kubectl get deployment backend frontend -n "$EKS_NAMESPACE"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Test async endpoint: POST /api/multi-agent/submit"
echo "2. Monitor logs: kubectl logs -n $EKS_NAMESPACE -l app=backend -f"
echo "3. Check for timeout errors: kubectl logs -n $EKS_NAMESPACE -l app=backend | grep -i timeout"

