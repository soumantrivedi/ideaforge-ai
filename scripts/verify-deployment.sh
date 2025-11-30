#!/bin/bash

# Verification script for ideaforge-ai deployment
# Checks: AI provider initialization, Agno agents, knowledge base preview

set -e

NAMESPACE="${K8S_NAMESPACE:-ideaforge-ai}"
CONTEXT="${K8S_CONTEXT:-kind-ideaforge-ai}"
INGRESS_PORT="${INGRESS_PORT:-8081}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-8000}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info "=========================================="
print_info "IdeaForge AI Deployment Verification"
print_info "=========================================="
echo ""

# 1. Check pod status
print_info "1. Checking pod status..."
PODS=$(kubectl get pods -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
if [ -z "${PODS}" ]; then
    print_error "No pods found in namespace ${NAMESPACE}"
    exit 1
fi

BACKEND_POD=$(kubectl get pods -n ${NAMESPACE} --context ${CONTEXT} -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -z "${BACKEND_POD}" ]; then
    print_error "Backend pod not found"
    exit 1
fi

print_success "Backend pod: ${BACKEND_POD}"
kubectl get pods -n ${NAMESPACE} --context ${CONTEXT} -l app=backend,app=frontend --no-headers | while read line; do
    STATUS=$(echo $line | awk '{print $3}')
    if [ "${STATUS}" = "Running" ]; then
        print_success "Pod: $(echo $line | awk '{print $1}') - ${STATUS}"
    else
        print_warning "Pod: $(echo $line | awk '{print $1}') - ${STATUS}"
    fi
done
echo ""

# 2. Check backend health
print_info "2. Checking backend health endpoint..."
HEALTH_URL="http://localhost:${INGRESS_PORT}/api/health"
HEALTH_RESPONSE=$(curl -s -f ${HEALTH_URL} 2>/dev/null || echo "")
if [ -z "${HEALTH_RESPONSE}" ]; then
    print_warning "Health endpoint not accessible via ingress, trying direct port-forward..."
    # Try port-forward
    kubectl port-forward -n ${NAMESPACE} --context ${CONTEXT} svc/backend 8000:8000 > /dev/null 2>&1 &
    PF_PID=$!
    sleep 2
    HEALTH_RESPONSE=$(curl -s http://localhost:${PORT_FORWARD_PORT}/api/health 2>/dev/null || echo "")
    kill $PF_PID 2>/dev/null || true
fi

if [ -n "${HEALTH_RESPONSE}" ]; then
    print_success "Backend health check passed"
    echo "${HEALTH_RESPONSE}" | jq '.' 2>/dev/null || echo "${HEALTH_RESPONSE}"
else
    print_error "Backend health check failed"
fi
echo ""

# 3. Check AI provider initialization
print_info "3. Checking AI provider initialization..."
print_info "Checking backend logs for provider initialization..."

# Check for provider registry initialization
PROVIDER_LOG=$(kubectl logs -n ${NAMESPACE} --context ${CONTEXT} ${BACKEND_POD} --tail=100 2>/dev/null | grep -i "provider\|openai\|claude\|gemini" | tail -5 || echo "")
if [ -n "${PROVIDER_LOG}" ]; then
    print_success "Found provider-related logs:"
    echo "${PROVIDER_LOG}"
else
    print_warning "No provider initialization logs found"
fi

# Check environment variables for API keys
print_info "Checking for API keys in secrets..."
API_KEYS=$(kubectl get secret ideaforge-ai-secrets -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data}' 2>/dev/null | jq -r 'keys[]' | grep -i "api_key\|key" || echo "")
if [ -n "${API_KEYS}" ]; then
    print_success "Found API key secrets:"
    echo "${API_KEYS}" | while read key; do
        HAS_VALUE=$(kubectl get secret ideaforge-ai-secrets -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath="{.data.${key}}" 2>/dev/null | base64 -d 2>/dev/null | wc -c || echo "0")
        if [ "${HAS_VALUE}" -gt "5" ]; then
            print_success "  ${key}: configured"
        else
            print_warning "  ${key}: empty or not set"
        fi
    done
else
    print_warning "No API key secrets found"
fi
echo ""

# 4. Check Agno agents initialization
print_info "4. Checking Agno agents initialization..."
AGNO_LOG=$(kubectl logs -n ${NAMESPACE} --context ${CONTEXT} ${BACKEND_POD} --tail=200 2>/dev/null | grep -i "agno\|orchestrator" | tail -10 || echo "")
if [ -n "${AGNO_LOG}" ]; then
    if echo "${AGNO_LOG}" | grep -qi "agno.*initialized\|agno.*enabled"; then
        print_success "Agno framework appears to be initialized"
    else
        print_warning "Agno framework may not be initialized"
    fi
    echo "${AGNO_LOG}"
else
    print_warning "No Agno-related logs found"
fi

# Check for Agno initialization endpoint
print_info "Testing Agno initialization endpoint..."
AGNO_INIT_RESPONSE=$(curl -s -X POST "http://localhost:${INGRESS_PORT}/api/agno/initialize" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test" 2>/dev/null || echo "")
if [ -n "${AGNO_INIT_RESPONSE}" ]; then
    if echo "${AGNO_INIT_RESPONSE}" | grep -qi "success\|agno_enabled"; then
        print_success "Agno initialization endpoint accessible"
    else
        print_warning "Agno initialization endpoint returned: ${AGNO_INIT_RESPONSE}"
    fi
else
    print_warning "Could not reach Agno initialization endpoint"
fi
echo ""

# 5. Check knowledge base article preview
print_info "5. Checking knowledge base article preview capability..."
print_info "Checking frontend code for preview functionality..."

# Check if KnowledgeBaseManager component exists and has preview
KB_PREVIEW_CHECK=$(grep -r "preview\|Preview" /Users/Souman_Trivedi/IdeaProjects/ideaforge-ai/src/components/KnowledgeBaseManager.tsx 2>/dev/null | head -3 || echo "")
if [ -n "${KB_PREVIEW_CHECK}" ]; then
    print_success "Knowledge base preview functionality found in frontend code"
    echo "Preview features detected:"
    echo "${KB_PREVIEW_CHECK}" | head -3
else
    print_warning "Knowledge base preview functionality not found"
fi

# Check backend API for knowledge articles
print_info "Checking backend API for knowledge articles endpoint..."
KB_API_RESPONSE=$(curl -s "http://localhost:${INGRESS_PORT}/api/db/knowledge-articles" \
    -H "Authorization: Bearer test" 2>/dev/null || echo "")
if [ -n "${KB_API_RESPONSE}" ]; then
    if echo "${KB_API_RESPONSE}" | grep -qi "articles\|knowledge"; then
        print_success "Knowledge articles API endpoint accessible"
    else
        print_warning "Knowledge articles API may not be working correctly"
    fi
else
    print_warning "Could not reach knowledge articles API (may require authentication)"
fi
echo ""

# 6. Summary
print_info "=========================================="
print_info "Verification Summary"
print_info "=========================================="

# Count issues
ISSUES=0

if [ -z "${HEALTH_RESPONSE}" ]; then
    print_error "❌ Backend health check failed"
    ISSUES=$((ISSUES + 1))
else
    print_success "✅ Backend health check passed"
fi

if [ -z "${AGNO_LOG}" ] || ! echo "${AGNO_LOG}" | grep -qi "agno.*initialized"; then
    print_warning "⚠️  Agno agents may not be initialized"
    ISSUES=$((ISSUES + 1))
else
    print_success "✅ Agno agents appear to be initialized"
fi

if [ -z "${KB_PREVIEW_CHECK}" ]; then
    print_warning "⚠️  Knowledge base preview may not be available"
    ISSUES=$((ISSUES + 1))
else
    print_success "✅ Knowledge base preview functionality exists"
fi

echo ""
if [ ${ISSUES} -eq 0 ]; then
    print_success "All checks passed! ✅"
    exit 0
else
    print_warning "Found ${ISSUES} potential issue(s). Please review the output above."
    exit 1
fi
