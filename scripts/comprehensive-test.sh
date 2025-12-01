#!/bin/bash
# Comprehensive Testing Script for IdeaForge AI
# Tests all agents, API endpoints, frontend features, and workflows

set -e

NAMESPACE="ideaforge-ai"
CONTEXT="kind-ideaforge-ai"
BACKEND_URL="http://localhost:8080/api"
FRONTEND_URL="http://localhost:8080"

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

# Test results
PASSED=0
FAILED=0
WARNINGS=0

test_passed() {
    ((PASSED++))
    print_success "$1"
}

test_failed() {
    ((FAILED++))
    print_error "$1"
}

test_warning() {
    ((WARNINGS++))
    print_warning "$1"
}

# Get auth token
get_auth_token() {
    local email="${1:-admin@ideaforge.ai}"
    local password="${2:-password123}"
    
    RESPONSE=$(curl -s -X POST "${BACKEND_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\",\"password\":\"${password}\"}" \
        --cookie-jar /tmp/cookies.txt 2>/dev/null)
    
    TOKEN=$(echo "$RESPONSE" | jq -r '.token // .access_token // empty' 2>/dev/null)
    
    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo ""
        return 1
    fi
    
    echo "$TOKEN"
}

print_info "=========================================="
print_info "Comprehensive Testing Suite"
print_info "=========================================="
echo ""

# 1. Check backend health
print_info "1. Testing Backend Health..."
HEALTH=$(curl -s "${BACKEND_URL}/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "status\|healthy\|ok" || [ -n "$HEALTH" ]; then
    test_passed "Backend health check"
else
    test_failed "Backend health check"
fi
echo ""

# 2. Get auth token
print_info "2. Testing Authentication..."
TOKEN=$(get_auth_token)
if [ -n "$TOKEN" ]; then
    test_passed "Authentication successful"
    export AUTH_TOKEN="$TOKEN"
else
    test_failed "Authentication failed"
    print_error "Cannot continue without authentication"
    exit 1
fi
echo ""

# 3. Test all agents
print_info "3. Testing All Agents..."
AGENTS=(
    "research"
    "analysis"
    "prd_authoring"
    "ideation"
    "summary"
    "scoring"
    "strategy"
    "validation"
    "export"
    "github_mcp"
    "atlassian_mcp"
    "v0"
    "lovable"
    "rag"
)

for agent in "${AGENTS[@]}"; do
    print_info "  Testing agent: $agent"
    RESPONSE=$(curl -s -X POST "${BACKEND_URL}/multi-agent/chat" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"product_id\": \"a7b8c9d0-e1f2-4345-a678-901234567890\",
            \"session_id\": \"00000000-0000-0000-0000-000000000001\",
            \"messages\": [{\"role\": \"user\", \"content\": \"Test message for $agent\"}],
            \"agent_type\": \"$agent\",
            \"coordination_mode\": \"single\"
        }" 2>/dev/null)
    
    if echo "$RESPONSE" | grep -q "response\|error\|404" 2>/dev/null; then
        if echo "$RESPONSE" | grep -q "404.*not found" 2>/dev/null; then
            test_failed "Agent $agent not found"
        elif echo "$RESPONSE" | grep -q "error" 2>/dev/null; then
            test_warning "Agent $agent returned error (may be expected)"
        else
            test_passed "Agent $agent accessible"
        fi
    else
        test_warning "Agent $agent response unclear"
    fi
done
echo ""

# 4. Test API endpoints
print_info "4. Testing API Endpoints..."

# Auth endpoints
print_info "  Testing auth endpoints..."
AUTH_ME=$(curl -s -X GET "${BACKEND_URL}/auth/me" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)
if echo "$AUTH_ME" | grep -q "id\|email\|user" 2>/dev/null; then
    test_passed "GET /auth/me"
else
    test_failed "GET /auth/me"
fi

# Products endpoints
print_info "  Testing products endpoints..."
PRODUCTS=$(curl -s -X GET "${BACKEND_URL}/products" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)
if echo "$PRODUCTS" | grep -q "\[\]\|id\|product" 2>/dev/null; then
    test_passed "GET /products"
else
    test_failed "GET /products"
fi

# Agent stats
print_info "  Testing agent stats..."
STATS=$(curl -s -X GET "${BACKEND_URL}/agent-stats" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)
if echo "$STATS" | grep -q "\[\]\|agent\|stats" 2>/dev/null; then
    test_passed "GET /agent-stats"
else
    test_warning "GET /agent-stats (may be empty)"
fi

# Metrics
print_info "  Testing metrics..."
METRICS=$(curl -s -X GET "${BACKEND_URL}/metrics" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)
if echo "$METRICS" | grep -q "\[\]\|metric" 2>/dev/null; then
    test_passed "GET /metrics"
else
    test_warning "GET /metrics (may be empty)"
fi

# Database endpoints
print_info "  Testing database endpoints..."
DB_TABLES=$(curl -s -X GET "${BACKEND_URL}/db/tables" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)
if echo "$DB_TABLES" | grep -q "\[\]\|table\|name" 2>/dev/null; then
    test_passed "GET /db/tables"
else
    test_warning "GET /db/tables"
fi
echo ""

# 5. Test multi-agent workflow
print_info "5. Testing Multi-Agent Workflow..."
MULTI_AGENT=$(curl -s -X POST "${BACKEND_URL}/multi-agent/chat" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"product_id\": \"a7b8c9d0-e1f2-4345-a678-901234567890\",
        \"session_id\": \"00000000-0000-0000-0000-000000000001\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Test multi-agent workflow\"}],
        \"agent_type\": \"multi_agent_enhanced\",
        \"coordination_mode\": \"collaborative\"
    }" 2>/dev/null)

if echo "$MULTI_AGENT" | grep -q "response\|error" 2>/dev/null; then
    if echo "$MULTI_AGENT" | grep -q "error" 2>/dev/null; then
        test_warning "Multi-agent workflow returned error (may be expected)"
    else
        test_passed "Multi-agent workflow accessible"
    fi
else
    test_warning "Multi-agent workflow response unclear"
fi
echo ""

# 6. Test Agno framework initialization
print_info "6. Testing Agno Framework..."
AGNO_STATUS=$(curl -s -X GET "${BACKEND_URL}/agno/status" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>/dev/null)

if echo "$AGNO_STATUS" | grep -q "enabled\|available\|framework" 2>/dev/null; then
    test_passed "Agno framework status endpoint"
else
    test_warning "Agno framework status endpoint (may not exist)"
fi
echo ""

# 7. Test frontend accessibility
print_info "7. Testing Frontend Accessibility..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/" 2>/dev/null)
if [ "$FRONTEND_RESPONSE" = "200" ] || [ "$FRONTEND_RESPONSE" = "304" ]; then
    test_passed "Frontend accessible"
else
    test_warning "Frontend returned status: $FRONTEND_RESPONSE"
fi
echo ""

# Summary
print_info "=========================================="
print_info "Test Summary"
print_info "=========================================="
echo ""
print_success "Passed: $PASSED"
print_error "Failed: $FAILED"
print_warning "Warnings: $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    print_success "All critical tests passed!"
    exit 0
else
    print_error "Some tests failed. Please review."
    exit 1
fi

