#!/bin/bash
# Verify Async Job Processing Endpoints
# Usage: ./scripts/verify-async-endpoints.sh [EKS_NAMESPACE] [BASE_URL]

set -e

EKS_NAMESPACE=${1:-"20890-ideaforge-ai-dev-58a50"}
BASE_URL=${2:-"https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud"}

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Verifying Async Job Processing Endpoints${NC}"
echo "=============================================="
echo "Namespace: $EKS_NAMESPACE"
echo "Base URL: $BASE_URL"
echo ""

# Get backend pod for internal testing
BACKEND_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$BACKEND_POD" ]; then
    echo -e "${RED}❌ Backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend pod: $BACKEND_POD${NC}"
echo ""

# Test 1: Check if async endpoints are registered
echo -e "${YELLOW}Test 1: Checking if async endpoints are registered...${NC}"
kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
    curl -s http://localhost:8000/openapi.json 2>/dev/null | \
    grep -o '"/api/multi-agent/submit\|/api/multi-agent/jobs' | head -3 || {
    echo -e "${RED}❌ Async endpoints not found in OpenAPI spec${NC}"
}

# Test 2: Check Redis connection
echo -e "${YELLOW}Test 2: Checking Redis connection...${NC}"
kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
    python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print('✅ Redis connected' if r.ping() else '❌ Redis not connected')" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Could not test Redis connection (may need redis package)${NC}"
}

# Test 3: Check job service import
echo -e "${YELLOW}Test 3: Checking job service import...${NC}"
kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
    python -c "from backend.services.job_service import job_service; print('✅ Job service imported successfully')" 2>/dev/null || {
    echo -e "${RED}❌ Job service import failed${NC}"
}

# Test 4: Check backend logs for async endpoints
echo -e "${YELLOW}Test 4: Checking backend logs for async endpoints...${NC}"
kubectl logs -n "$EKS_NAMESPACE" "$BACKEND_POD" --tail=100 | grep -i "job\|async\|submit" | head -5 || {
    echo -e "${YELLOW}⚠️  No async endpoint logs found (may need to trigger an endpoint)${NC}"
}

# Test 5: Health check
echo -e "${YELLOW}Test 5: Health check...${NC}"
HEALTH=$(kubectl exec -n "$EKS_NAMESPACE" "$BACKEND_POD" -- \
    curl -s http://localhost:8000/health 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q "status"; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
fi

echo ""
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo "===================="
kubectl get pods -n "$EKS_NAMESPACE" -l 'app in (backend,frontend,redis)'
echo ""
echo -e "${BLUE}Image Tags:${NC}"
kubectl get deployment backend -n "$EKS_NAMESPACE" -o jsonpath='Backend: {.spec.template.spec.containers[0].image}{"\n"}' 2>/dev/null
kubectl get deployment frontend -n "$EKS_NAMESPACE" -o jsonpath='Frontend: {.spec.template.spec.containers[0].image}{"\n"}' 2>/dev/null

echo ""
echo -e "${GREEN}✅ Verification Complete!${NC}"
echo ""
echo -e "${YELLOW}📝 Manual Testing:${NC}"
echo "1. Submit job: curl -X POST $BASE_URL/api/multi-agent/submit -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' -d '{\"request\": {...}}'"
echo "2. Check status: curl -X GET $BASE_URL/api/multi-agent/jobs/{job_id}/status -H 'Authorization: Bearer TOKEN'"
echo "3. Get result: curl -X GET $BASE_URL/api/multi-agent/jobs/{job_id}/result -H 'Authorization: Bearer TOKEN'"

