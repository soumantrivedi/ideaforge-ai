#!/bin/bash
# Test script to check V0 project status directly using V0 API
# Tests the check-status functionality with projectId (camelCase)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "V0 Check Status Test"
echo "============================================================"

# Load .env file if it exists
if [ -f .env ]; then
    echo -e "${GREEN}✅ Loading .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}⚠️  .env file not found, using system environment variables${NC}"
fi

# Check if V0_API_KEY is set
if [ -z "$V0_API_KEY" ]; then
    echo -e "${RED}❌ V0_API_KEY environment variable is required${NC}"
    echo "   Set it in .env file or export V0_API_KEY=your-key"
    exit 1
fi

# Test payload data
PRODUCT_ID="a7b8c9d0-e1f2-4345-a678-901234567890"
PROJECT_ID="J8hZlPsWQdX"  # Using projectId (camelCase) as per V0 API format
PROVIDER="v0"

echo ""
echo "📋 Test Payload:"
echo "   product_id: $PRODUCT_ID"
echo "   projectId: $PROJECT_ID"
echo "   provider: $PROVIDER"
echo ""

# Step 1: Get project details
echo "📡 Step 1: Fetching project details..."
echo "   URL: https://api.v0.dev/v1/projects/$PROJECT_ID"
echo ""

PROJECT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $V0_API_KEY" \
    -H "Content-Type: application/json" \
    "https://api.v0.dev/v1/projects/$PROJECT_ID")

# Split response and status code (macOS compatible)
PROJECT_BODY=$(echo "$PROJECT_RESPONSE" | sed '$d')
PROJECT_STATUS=$(echo "$PROJECT_RESPONSE" | tail -n 1)

echo "   Status Code: $PROJECT_STATUS"

if [ "$PROJECT_STATUS" = "404" ]; then
    echo -e "${RED}❌ Project not found${NC}"
    echo "{\"projectId\":\"$PROJECT_ID\",\"project_id\":\"$PROJECT_ID\",\"project_status\":\"unknown\",\"error\":\"Project not found\"}"
    exit 1
fi

if [ "$PROJECT_STATUS" != "200" ]; then
    echo -e "${RED}❌ Error: Failed to get project${NC}"
    echo "$PROJECT_BODY"
    exit 1
fi

echo -e "${GREEN}✅ Project found${NC}"

# Extract chat ID from project data
CHAT_ID=$(echo "$PROJECT_BODY" | python3 -c "import sys, json; data = json.load(sys.stdin); chats = data.get('chats', []); print(chats[0].get('id', '') if chats else '')" 2>/dev/null || echo "")

if [ -z "$CHAT_ID" ]; then
    echo -e "${YELLOW}⚠️  No chats found in project${NC}"
    echo "{\"projectId\":\"$PROJECT_ID\",\"project_id\":\"$PROJECT_ID\",\"project_status\":\"pending\",\"note\":\"No chats found in project\"}"
    exit 0
fi

echo "   Chat ID: $CHAT_ID"
echo ""

# Step 2: Get chat details
echo "📡 Step 2: Fetching latest chat details..."
echo "   URL: https://api.v0.dev/v1/chats/$CHAT_ID"
echo ""

CHAT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $V0_API_KEY" \
    -H "Content-Type: application/json" \
    "https://api.v0.dev/v1/chats/$CHAT_ID")

# Split response and status code (macOS compatible)
CHAT_BODY=$(echo "$CHAT_RESPONSE" | sed '$d')
CHAT_STATUS=$(echo "$CHAT_RESPONSE" | tail -n 1)

echo "   Status Code: $CHAT_STATUS"

if [ "$CHAT_STATUS" != "200" ]; then
    echo -e "${RED}❌ Error: Failed to get chat${NC}"
    echo "$CHAT_BODY"
    exit 1
fi

echo -e "${GREEN}✅ Chat found${NC}"
echo ""

# Extract status information using Python (save to temp file to avoid shell escaping issues)
TEMP_FILE=$(mktemp)
echo "$CHAT_BODY" > "$TEMP_FILE"

echo "📊 Status Summary:"
RESULT=$(python3 << PYTHON_SCRIPT
import sys
import json

project_id = "$PROJECT_ID"
temp_file = "$TEMP_FILE"

try:
    with open(temp_file, 'r') as f:
        chat_data = json.load(f)
    
    # Extract URLs (V0 API uses camelCase)
    web_url = chat_data.get("webUrl") or chat_data.get("web_url") or ""
    demo_url = chat_data.get("demo") or chat_data.get("demoUrl") or chat_data.get("demo_url") or ""
    files = chat_data.get("files", [])
    
    # Determine status
    is_complete = bool(demo_url or web_url or (files and len(files) > 0))
    project_status = "completed" if is_complete else "in_progress"
    project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_data.get('id', '')}" if chat_data.get('id') else "")
    
    result = {
        "projectId": project_id,
        "project_id": project_id,
        "chat_id": chat_data.get("id"),
        "project_status": project_status,
        "project_url": project_url,
        "web_url": web_url,
        "demo_url": demo_url,
        "is_complete": is_complete,
        "num_files": len(files)
    }
    
    print(f"   Web URL: {web_url}")
    print(f"   Demo URL: {demo_url}")
    print(f"   Files: {len(files)}")
    print(f"   Status: {project_status}")
    print(f"   Is Complete: {is_complete}")
    print(f"   Project URL: {project_url}")
    print("")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error parsing response: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
)

# Clean up temp file
rm -f "$TEMP_FILE"

echo ""
echo "============================================================"
echo "✅ Test Results"
echo "============================================================"
echo "$RESULT" | tail -n +9  # Skip the status summary lines, show only JSON

# Validate response format
echo ""
echo "🔍 Response Validation:"
if echo "$RESULT" | grep -q '"projectId"'; then
    echo -e "   ${GREEN}✅ projectId (camelCase) found${NC}"
else
    echo -e "   ${RED}❌ Missing projectId (camelCase)${NC}"
fi

if echo "$RESULT" | grep -q '"project_id"'; then
    echo -e "   ${GREEN}✅ project_id (snake_case) found${NC}"
else
    echo -e "   ${RED}❌ Missing project_id (snake_case)${NC}"
fi

if echo "$RESULT" | grep -q '"project_status"'; then
    echo -e "   ${GREEN}✅ project_status found${NC}"
else
    echo -e "   ${RED}❌ Missing project_status${NC}"
fi

if echo "$RESULT" | grep -q '"is_complete"'; then
    echo -e "   ${GREEN}✅ is_complete found${NC}"
else
    echo -e "   ${RED}❌ Missing is_complete${NC}"
fi

echo ""
echo -e "${GREEN}✅ Test completed successfully!${NC}"

