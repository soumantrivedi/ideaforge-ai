#!/bin/bash
# Test AI Gateway credentials directly

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}

echo "🧪 Testing AI Gateway Credentials"
echo "================================="
echo ""

BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend --context $CONTEXT -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$BACKEND_POD" ]; then
    echo "❌ Backend pod not found"
    exit 1
fi

echo "Using backend pod: $BACKEND_POD"
echo ""

echo "1️⃣  Testing AI Gateway Client Initialization..."
kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "
import asyncio
import os
from backend.services.ai_gateway_client import AIGatewayClient

async def test():
    client_id = os.getenv('AI_GATEWAY_CLIENT_ID')
    client_secret = os.getenv('AI_GATEWAY_CLIENT_SECRET')
    base_url = os.getenv('AI_GATEWAY_BASE_URL', 'https://ai-gateway.quantumblack.com')
    
    if not client_id or not client_secret:
        print('❌ AI Gateway credentials not found in environment')
        return
    
    print(f'✅ Credentials found')
    print(f'   Client ID: {client_id[:20]}...')
    print(f'   Base URL: {base_url}')
    print('')
    print('2️⃣  Testing OAuth2 Token Acquisition...')
    
    client = AIGatewayClient(client_id, client_secret, base_url=base_url)
    try:
        token = await client._get_access_token()
        if token:
            print(f'✅ Access token obtained: {token[:30]}...')
        else:
            print('❌ Failed to obtain access token')
            return
    except Exception as e:
        print(f'❌ Token acquisition failed: {str(e)[:200]}')
        return
    
    print('')
    print('3️⃣  Testing Model Listing...')
    try:
        models = await client.list_models()
        print(f'✅ Successfully listed {len(models)} models')
        if models:
            print('   Available models:')
            for model in models[:5]:
                model_id = model.get('id', 'N/A')
                model_name = model.get('name', model_id)
                print(f'     - {model_id} ({model_name})')
    except Exception as e:
        print(f'❌ Model listing failed: {str(e)[:200]}')
        return
    
    print('')
    print('4️⃣  Testing Credential Verification...')
    try:
        is_valid = await client.verify_credentials()
        if is_valid:
            print('✅ Credentials are valid!')
        else:
            print('❌ Credentials verification failed')
    except Exception as e:
        print(f'❌ Verification error: {str(e)[:200]}')
    finally:
        await client.close()

asyncio.run(test())
" 2>&1

echo ""
echo "✅ AI Gateway Credential Test Complete!"

