#!/bin/bash
# User Journey Verification Script
# Tests all navigation paths and ensures no errors occur

set -e

API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3001}"

echo "=== User Journey Verification ==="
echo "API URL: $API_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    local expected_status=$5
    
    echo -n "Testing $name... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $TOKEN" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Authorization: Bearer $TOKEN" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got $http_code)"
        echo "Response: $body"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Step 1: Login
echo "=== Step 1: Authentication ==="
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@ideaforge.ai","password":"password123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo ""

# Step 2: Test API Endpoints
echo "=== Step 2: API Endpoints ==="
test_endpoint "Get User Profile" "GET" "$API_URL/api/users/profile" "" "200"
test_endpoint "Get User Preferences" "GET" "$API_URL/api/users/preferences" "" "200"
test_endpoint "List Products" "GET" "$API_URL/api/products" "" "200"
test_endpoint "Get Portfolio" "GET" "$API_URL/api/products/portfolio" "" "200"
test_endpoint "Get Conversation History" "GET" "$API_URL/api/conversations/history" "" "200"
echo ""

# Step 3: Test Product Creation
echo "=== Step 3: Product Management ==="
PRODUCT_DATA='{"name":"Test Product '$(date +%s)'","description":"Test product for verification"}'
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/api/products" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$PRODUCT_DATA")

PRODUCT_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -n "$PRODUCT_ID" ]; then
    echo -e "${GREEN}✓ Product created: $PRODUCT_ID${NC}"
    test_endpoint "Get Product" "GET" "$API_URL/api/products/$PRODUCT_ID" "" "200"
    test_endpoint "Update Product" "PUT" "$API_URL/api/products/$PRODUCT_ID" '{"name":"Updated Test Product"}' "200"
    test_endpoint "Delete Product" "DELETE" "$API_URL/api/products/$PRODUCT_ID" "" "200"
else
    echo -e "${RED}✗ Product creation failed${NC}"
    echo "Response: $CREATE_RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Step 4: Test Preferences Update
echo "=== Step 4: User Preferences ==="
test_endpoint "Update Preferences" "PUT" "$API_URL/api/users/preferences" \
    '{"theme":"dark","language":"en","notifications_enabled":true}' "200"
echo ""

# Step 5: Verify Frontend Routes
echo "=== Step 5: Frontend Routes ==="
echo "Note: Frontend route testing requires browser automation"
echo "Manual verification checklist:"
echo "  [ ] Login page loads"
echo "  [ ] Dashboard loads after login"
echo "  [ ] Can navigate to Chat (with product selected)"
echo "  [ ] Can navigate to Knowledge Base"
echo "  [ ] Can navigate to Portfolio"
echo "  [ ] Can navigate to History"
echo "  [ ] Can navigate to Profile"
echo "  [ ] Can navigate to Settings"
echo "  [ ] Can navigate back to Dashboard from any route"
echo "  [ ] No console errors in browser"
echo ""

# Summary
echo "=== Summary ==="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All API tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

