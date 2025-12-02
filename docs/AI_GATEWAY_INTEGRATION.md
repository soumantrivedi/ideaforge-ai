# AI Gateway Integration

This document describes the AI Gateway integration for the IdeaForgeAI platform.

## Overview

AI Gateway provides unified access to multiple AI models through a single service account-based authentication system. This integration allows the platform to use AI Gateway alongside existing providers (OpenAI, Anthropic, Gemini) without replacing them.

## Architecture

### Components

1. **AIGatewayClient** (`backend/services/ai_gateway_client.py`)
   - Handles OAuth2 client credentials flow for service account authentication
   - Manages token refresh automatically
   - Provides methods for listing models and creating chat completions

2. **AIGatewayModel** (`backend/models/ai_gateway_model.py`)
   - Agno-compatible model wrapper
   - Implements the interface expected by Agno agents
   - Supports both sync and async generation

3. **ProviderRegistry** (`backend/services/provider_registry.py`)
   - Extended to support AI Gateway credentials
   - Manages AI Gateway client lifecycle
   - Provides unified interface for all providers

4. **Agno Integration** (`backend/agents/agno_base_agent.py`)
   - Updated to support AI Gateway as a provider option
   - Priority: AI Gateway (if enabled) > OpenAI > Gemini > Claude

## Configuration

### Environment Variables

```bash
# AI Gateway Configuration
AI_GATEWAY_CLIENT_ID=your_client_id
AI_GATEWAY_CLIENT_SECRET=your_client_secret
AI_GATEWAY_BASE_URL=https://ai-gateway.quantumblack.com  # Optional
AI_GATEWAY_ENABLED=true  # Enable AI Gateway as default provider
AI_GATEWAY_DEFAULT_MODEL=gpt-4o  # Default model to use
AI_GATEWAY_FAST_MODEL=gpt-4o-mini  # Model for fast tier
AI_GATEWAY_STANDARD_MODEL=gpt-4o  # Model for standard tier
AI_GATEWAY_PREMIUM_MODEL=gpt-4-turbo  # Model for premium tier
```

### User Settings

Users can configure AI Gateway credentials through the Settings UI:
- Client ID (service account client ID)
- Client Secret (service account client secret)
- Base URL (optional, defaults to environment setting)
- Default Model (optional, defaults to environment setting)

## Database Schema

AI Gateway credentials are stored in the `user_api_keys` table:
- `provider`: 'ai_gateway'
- `api_key_encrypted`: Encrypted client_id
- `metadata`: JSON containing:
  - `client_secret`: Encrypted client_secret
  - `base_url`: Optional base URL override
  - `default_model`: Optional default model override

## API Endpoints

### Verify AI Gateway Credentials

```http
POST /api/providers/verify
Content-Type: application/json

{
  "provider": "ai_gateway",
  "api_key": "client_id",
  "client_secret": "client_secret",
  "base_url": "https://ai-gateway.quantumblack.com"  // Optional
}
```

### Configure AI Gateway

```http
POST /api/providers/configure
Content-Type: application/json

{
  "aiGatewayClientId": "client_id",
  "aiGatewayClientSecret": "client_secret",
  "aiGatewayBaseUrl": "https://ai-gateway.quantumblack.com",  // Optional
  "aiGatewayDefaultModel": "gpt-4o"  // Optional
}
```

## Usage

### In Agno Agents

AI Gateway is automatically used when:
1. `AI_GATEWAY_ENABLED=true` is set, OR
2. User has configured AI Gateway credentials in Settings

The agent will prioritize AI Gateway over other providers if enabled.

### Model Selection

Models are selected based on the agent tier:
- **Fast tier**: Uses `AI_GATEWAY_FAST_MODEL` (default: gpt-4o-mini)
- **Standard tier**: Uses `AI_GATEWAY_STANDARD_MODEL` (default: gpt-4o)
- **Premium tier**: Uses `AI_GATEWAY_PREMIUM_MODEL` (default: gpt-4-turbo)

Or uses the user-configured default model if set.

## Testing

Run the test suite:

```bash
pytest backend/tests/test_ai_gateway.py -v
```

## Validation

### Credential Verification

The platform validates AI Gateway credentials by:
1. Obtaining an OAuth2 access token using client credentials
2. Attempting to list available models
3. Returning success if both steps succeed

### Model Availability

Before using a model, the platform can check if it's available:

```python
from backend.services.provider_registry import provider_registry

if provider_registry.has_ai_gateway():
    client = provider_registry.get_ai_gateway_client()
    models = await client.list_models()
    # Check if desired model is in the list
```

## Troubleshooting

### Token Refresh Issues

If you encounter token refresh errors:
1. Verify client_id and client_secret are correct
2. Check network connectivity to AI Gateway
3. Verify base_url is correct

### Model Not Found

If a model is not available:
1. Check available models: `await client.list_models()`
2. Update `AI_GATEWAY_DEFAULT_MODEL` or user settings
3. Ensure the model ID matches exactly (case-sensitive)

### Integration with Existing Providers

AI Gateway works alongside existing providers:
- If AI Gateway is enabled, it takes priority
- If AI Gateway fails, the system falls back to other providers
- Users can disable AI Gateway via environment variable or settings

## Security

- All credentials are encrypted at rest
- Client secrets are never logged
- Tokens are refreshed automatically before expiry
- Service account credentials follow OAuth2 best practices

## References

- [AI Gateway API Reference](https://docs.prod.ai-gateway.quantumblack.com/getting_started/ai_gateway_api_reference/)
- [Service Accounts Documentation](https://docs.prod.ai-gateway.quantumblack.com/getting_started/service_accounts/)
- [Available Models](https://docs.prod.ai-gateway.quantumblack.com/models/)

