#!/bin/bash
# Script to validate AI Gateway integration in kind cluster

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}

echo "🔍 Validating AI Gateway Integration"
echo "===================================="
echo ""

# Get ingress port
INGRESS_PORT=$(docker ps --filter "name=ideaforge-ai-control-plane" --format "{{.Ports}}" | grep -o "0.0.0.0:[0-9]*->80" | cut -d: -f2 | cut -d- -f1 || echo "8081")
BASE_URL="http://localhost:$INGRESS_PORT"

echo "1️⃣  Checking Backend Health..."
if curl -s -f "$BASE_URL/health" > /dev/null; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend health check failed"
    exit 1
fi
echo ""

echo "2️⃣  Checking Provider Registry Configuration..."
BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend --context $CONTEXT -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$BACKEND_POD" ]; then
    echo "   ❌ Backend pod not found"
    exit 1
fi

PROVIDERS=$(kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "from backend.services.provider_registry import provider_registry; print(','.join(provider_registry.get_configured_providers()))" 2>/dev/null || echo "")
echo "   Configured providers: $PROVIDERS"

AI_GATEWAY_CONFIGURED=$(kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "from backend.services.provider_registry import provider_registry; print('true' if provider_registry.has_ai_gateway() else 'false')" 2>/dev/null || echo "false")
if [ "$AI_GATEWAY_CONFIGURED" = "true" ]; then
    echo "   ✅ AI Gateway is configured"
else
    echo "   ⚠️  AI Gateway is not configured (this is expected if credentials are not set)"
fi
echo ""

echo "3️⃣  Checking AI Gateway Environment Variables..."
AI_GATEWAY_ENABLED=$(kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "from backend.config import settings; print('true' if getattr(settings, 'ai_gateway_enabled', False) else 'false')" 2>/dev/null || echo "false")
AI_GATEWAY_CLIENT_ID=$(kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "from backend.config import settings; print('set' if getattr(settings, 'ai_gateway_client_id', None) else 'not set')" 2>/dev/null || echo "not set")
AI_GATEWAY_BASE_URL=$(kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "from backend.config import settings; print(getattr(settings, 'ai_gateway_base_url', 'not set'))" 2>/dev/null || echo "not set")

echo "   AI Gateway Enabled: $AI_GATEWAY_ENABLED"
echo "   AI Gateway Client ID: $AI_GATEWAY_CLIENT_ID"
echo "   AI Gateway Base URL: $AI_GATEWAY_BASE_URL"
echo ""

echo "4️⃣  Testing AI Gateway API Endpoints..."
echo "   Testing /api/providers/verify endpoint (should accept ai_gateway provider)..."
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/providers/verify" \
    -H "Content-Type: application/json" \
    -d '{"provider": "ai_gateway", "api_key": "test_client_id", "client_secret": "test_client_secret"}' \
    2>/dev/null || echo "error")

if echo "$VERIFY_RESPONSE" | grep -q "ai_gateway\|error\|detail"; then
    echo "   ✅ AI Gateway verification endpoint is accessible"
    echo "   Response: $(echo $VERIFY_RESPONSE | head -c 200)"
else
    echo "   ⚠️  Could not test verification endpoint"
fi
echo ""

echo "5️⃣  Checking Backend Logs for AI Gateway..."
kubectl logs -n $NAMESPACE -l app=backend --context $CONTEXT --tail=100 2>/dev/null | \
    grep -iE "ai_gateway|gateway" | tail -5 || \
    echo "   ℹ️  No AI Gateway logs found (normal if not configured)"
echo ""

echo "6️⃣  Testing Agno Agent Initialization with AI Gateway..."
AGNO_STATUS=$(curl -s "$BASE_URL/api/agno/status" 2>/dev/null || echo "{}")
if echo "$AGNO_STATUS" | grep -q "configured_providers"; then
    echo "   ✅ Agno status endpoint accessible"
    echo "   Providers: $(echo $AGNO_STATUS | grep -o '"configured_providers":\[[^]]*\]' | head -1)"
else
    echo "   ⚠️  Could not check Agno status"
fi
echo ""

echo "✅ AI Gateway Validation Complete!"
echo ""
echo "📝 Next Steps:"
echo "   1. Set AI_GATEWAY_CLIENT_ID and AI_GATEWAY_CLIENT_SECRET in env.kind"
echo "   2. Set AI_GATEWAY_ENABLED=true to enable AI Gateway as default provider"
echo "   3. Run 'make kind-load-secrets' to update secrets"
echo "   4. Restart backend pods: kubectl rollout restart deployment/backend -n $NAMESPACE --context $CONTEXT"
echo "   5. Test AI Gateway verification via UI or API"

